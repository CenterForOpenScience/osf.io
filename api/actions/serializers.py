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
from reviews.workflow import Triggers
from reviews.workflow import States


# Pseudo-class to hide the creator field if it shouldn't be shown
def HideIfCommentsAnonymous(field_cls):
    class HideIfCommentsAnonymousField(field_cls):
        def get_attribute(self, instance):
            request = self.context.get('request')
            if request is not None:
                auth = utils.get_user_auth(request)
                if auth.logged_in:
                    provider = instance.target.provider
                    if provider.reviews_comments_anonymous is False or auth.user.has_perm('view_actions', provider):
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
                    provider = instance.target.provider
                    if provider.reviews_comments_private is False or auth.user.has_perm('view_actions', provider):
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
        is_detail = self.context.get('view') and not isinstance(self.context['view'], generics.ListAPIView)
        # Weird hack to avoid being called twice
        # get_meta_information is called with both self.related_meta and self.self_meta.
        # `is` could probably be used here but this seems more comprehensive.
        is_related_meta = metadata.pop('include_status_counts', False)

        if show_counts and is_detail and is_related_meta:
            # Finally, require users to have view_actions permissions
            auth = utils.get_user_auth(self.context['request'])
            if auth and auth.logged_in and auth.user.has_perm('view_actions', provider):
                metadata.update(provider.get_reviewable_status_counts())

        return super(ReviewableCountsRelationshipField, self).get_meta_information(metadata, provider)


class TargetRelationshipField(RelationshipField):
    def get_object(self, preprint_id):
        return PreprintService.objects.get(guids___id=preprint_id)

    def to_internal_value(self, data):
        preprint = self.get_object(data)
        return {'target': preprint}


class ActionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'trigger',
        'from_state',
        'to_state',
        'date_created',
        'date_modified',
        'provider',
        'target',
    ])

    id = ser.CharField(source='_id', read_only=True)

    trigger = ser.ChoiceField(choices=Triggers.choices())

    # TODO what limit do we want?
    comment = HideIfCommentsPrivate(ser.CharField)(max_length=65535, required=False)

    from_state = ser.ChoiceField(choices=States.choices(), read_only=True)
    to_state = ser.ChoiceField(choices=States.choices(), read_only=True)

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    provider = RelationshipField(
        read_only=True,
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<target.provider._id>'},
        filter_key='target__provider___id',
    )

    target = TargetRelationshipField(
        read_only=False,
        required=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<target._id>'},
        filter_key='target__guids___id',
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
            'self': 'get_action_url',
        }
    )

    def get_absolute_url(self, obj):
        return self.get_action_url(obj)

    def get_action_url(self, obj):
        return utils.absolute_reverse('actions:action-detail', kwargs={'action_id': obj._id, 'version': self.context['request'].parser_context['kwargs']['version']})

    def create(self, validated_data):
        trigger = validated_data.pop('trigger')
        user = validated_data.pop('user')
        target = validated_data.pop('target')
        comment = validated_data.pop('comment', '')
        try:
            if trigger == Triggers.ACCEPT.value:
                return target.reviews_accept(user, comment)
            if trigger == Triggers.REJECT.value:
                return target.reviews_reject(user, comment)
            if trigger == Triggers.EDIT_COMMENT.value:
                return target.reviews_edit_comment(user, comment)
            if trigger == Triggers.SUBMIT.value:
                return target.reviews_submit(user)
        except InvalidTransitionError:
            # Invalid transition from the current state
            raise JSONAPIAttributeException(attribute='trigger', detail='Cannot trigger "{}" from state "{}"'.format(trigger, target.reviews_state))
        else:
            raise JSONAPIAttributeException(attribute='trigger', detail='Invalid trigger.')

    class Meta:
        type_ = 'actions'
