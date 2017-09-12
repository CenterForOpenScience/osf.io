# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import serializers as ser
from rest_framework.fields import SkipField

from api.base import utils
from api.base.exceptions import JSONAPIAttributeException
from api.base.serializers import JSONAPISerializer
from api.base.serializers import LinksField
from api.base.serializers import RelationshipField

from osf.models import PreprintService

from reviews.exceptions import InvalidTransitionError
from reviews.workflow import Actions
from reviews.workflow import States


# Pseudo-class to hide the creator field if it shouldn't be shown
def HideIfCommentsAnonymous(field_cls):
    class HideIfCommentsAnonymousField(field_cls):
        def get_attribute(self, instance):
            request = self.context.get('request')
            if request is not None:
                auth = utils.get_user_auth(request)
                if auth.logged_in:
                    provider = instance.reviewable.provider
                    if provider.reviews_comments_anonymous is False or auth.user.has_perm('view_review_logs', provider):
                        return super(HideIfCommentsAnonymousField, self).get_attribute(instance)
            raise SkipField

        def __repr__(self):
            r = super(HideIfCommentsAnonymousField, self).__repr__()
            return r.replace(self.__class__.__name__, '{}<{}>'.format(self.__class__.__name__, field_cls.__name__))

    return HideIfCommentsAnonymousField


# Pseudo-class to hide the comment field if it shouldn't be shown
def HideIfCommentsPrivate(field_cls):
    class HideIfCommentsPrivateField(field_cls):
        def get_attribute(self, instance):
            request = self.context.get('request')
            if request is not None:
                auth = utils.get_user_auth(request)
                if auth.logged_in:
                    provider = instance.reviewable.provider
                    if provider.reviews_comments_private is False or auth.user.has_perm('view_review_logs', provider):
                        return super(HideIfCommentsPrivateField, self).get_attribute(instance)
            raise SkipField

        def __repr__(self):
            r = super(HideIfCommentsPrivateField, self).__repr__()
            return r.replace(self.__class__.__name__, '{}<{}>'.format(self.__class__.__name__, field_cls.__name__))

    return HideIfCommentsPrivateField


class ReviewableCountsRelationshipField(RelationshipField):

    def __init__(self, *args, **kwargs):
        kwargs['related_meta'] = kwargs.get('related_meta') or {}
        if 'include_status_counts' not in kwargs['related_meta']:
            kwargs['related_meta']['include_status_counts'] = True
        super(ReviewableCountsRelationshipField, self).__init__(*args, **kwargs)

    def get_meta_information(self, metadata, provider):
        # Clone metadata because it's mutablity is questionable
        metadata = dict(metadata or {})

        # Make counts opt in
        show_counts = utils.is_truthy(self.context['request'].query_params.get('related_counts', False))
        # Only include counts on detail routes
        is_detail = not isinstance(self.context['view'], generics.ListAPIView)
        # Weird hack to avoid being called twice
        # get_meta_information is called with both self.related_meta and self.self_meta.
        # `is` could probably be used here but this seems more comprehensive.
        is_related_meta = metadata.pop('include_status_counts', False)

        if show_counts and is_detail and is_related_meta:
            # Finally, require users to have view_review_logs permissions
            auth = utils.get_user_auth(self.context['request'])
            if auth and auth.logged_in and auth.user.has_perm('view_review_logs', provider):
                metadata.update(provider.get_reviewable_status_counts())

        return super(ReviewableCountsRelationshipField, self).get_meta_information(metadata, provider)


class ReviewableRelationshipField(RelationshipField):
    def get_object(self, preprint_id):
        return PreprintService.objects.get(guids___id=preprint_id)

    def to_internal_value(self, data):
        preprint = self.get_object(data)
        return {'reviewable': preprint}


class ReviewLogSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'action',
        'from_state',
        'to_state',
        'date_created',
        'date_modified',
        'provider',
        'reviewable',
    ])

    id = ser.CharField(source='_id', read_only=True)

    action = ser.ChoiceField(choices=Actions.choices())

    # TODO what limit do we want?
    comment = HideIfCommentsPrivate(ser.CharField)(max_length=65535, required=False)

    from_state = ser.ChoiceField(choices=States.choices(), read_only=True)
    to_state = ser.ChoiceField(choices=States.choices(), read_only=True)

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    provider = RelationshipField(
        read_only=True,
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<reviewable.provider._id>'},
        filter_key='reviewable__provider___id',
    )

    reviewable = ReviewableRelationshipField(
        read_only=False,
        required=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<reviewable._id>'},
        filter_key='reviewable__guids___id',
    )

    creator = HideIfCommentsAnonymous(RelationshipField)(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
        filter_key='creator__guids___id',
        always_embed=True,
    )

    links = LinksField(
        {
            'self': 'get_log_url',
        }
    )

    def get_absolute_url(self, obj):
        return self.get_log_url(obj)

    def get_log_url(self, obj):
        return utils.absolute_reverse('reviews:review_log-detail', kwargs={'log_id': obj._id, 'version': self.context['request'].parser_context['kwargs']['version']})

    def create(self, validated_data):
        action = validated_data.pop('action')
        user = validated_data.pop('user')
        reviewable = validated_data.pop('reviewable')
        comment = validated_data.pop('comment', '')
        try:
            if action == Actions.ACCEPT.value:
                return reviewable.reviews_accept(user, comment)
            if action == Actions.REJECT.value:
                return reviewable.reviews_reject(user, comment)
            if action == Actions.EDIT_COMMENT.value:
                return reviewable.reviews_edit_comment(user, comment)
            if action == Actions.SUBMIT.value:
                return reviewable.reviews_submit(user)
        except InvalidTransitionError:
            # Invalid transition from the current state
            raise JSONAPIAttributeException(attribute='action', detail='Cannot perform action "{}" from state "{}"'.format(action, reviewable.reviews_state))
        else:
            raise JSONAPIAttributeException(attribute='action', detail='Invalid action.')

    class Meta:
        type_ = 'review_logs'
