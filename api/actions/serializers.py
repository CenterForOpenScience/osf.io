# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import serializers as ser
from rest_framework import status as http_status
from rest_framework.exceptions import PermissionDenied
from transitions import MachineError

from framework.exceptions import HTTPError, PermissionsError

from api.base import utils
from api.base.exceptions import Conflict
from api.base.exceptions import JSONAPIAttributeException
from api.base.serializers import get_meta_type
from api.base.serializers import JSONAPISerializer
from api.base.serializers import LinksField
from api.base.serializers import RelationshipField
from api.base.serializers import HideIfProviderCommentsAnonymous
from api.base.serializers import HideIfProviderCommentsPrivate
from api.requests.serializers import PreprintRequestSerializer
from osf.exceptions import InvalidTriggerError
from osf.models import Preprint, NodeRequest, PreprintRequest, Registration
from osf.utils.workflows import (
    DefaultStates,
    DefaultTriggers,
    ReviewStates,
    ReviewTriggers,
    RegistrationModerationTriggers,
)
from osf.utils import permissions


class ReviewableCountsRelationshipField(RelationshipField):

    def __init__(self, *args, **kwargs):
        kwargs['related_meta'] = kwargs.get('related_meta') or {}
        if 'include_state_counts' not in kwargs['related_meta']:
            kwargs['related_meta']['include_state_counts'] = True
        super(ReviewableCountsRelationshipField, self).__init__(*args, **kwargs)

    def get_meta_information(self, metadata, provider):
        # Clone metadata because its mutability is questionable
        metadata = dict(metadata or {})

        # Make counts opt-in
        show_counts = utils.is_truthy(self.context['request'].query_params.get('related_counts', False))
        # Only include counts on detail routes
        is_detail = self.context.get('view') and not isinstance(self.context['view'], generics.ListAPIView)
        # Weird hack to avoid being called twice
        # get_meta_information is called with both self.related_meta and self.self_meta.
        # `is` could probably be used here but this seems more comprehensive.
        is_related_meta = metadata.pop('include_state_counts', False)

        if show_counts and is_detail and is_related_meta:
            # Finally, require users to have view_actions permissions
            auth = utils.get_user_auth(self.context['request'])
            if auth and auth.logged_in and auth.user.has_perm('view_actions', provider):
                metadata.update(provider.get_reviewable_state_counts())

        return super(ReviewableCountsRelationshipField, self).get_meta_information(metadata, provider)


class TargetRelationshipField(RelationshipField):
    _target_class = None

    def __init__(self, *args, **kwargs):
        self._target_class = kwargs.pop('target_class', None)
        super(TargetRelationshipField, self).__init__(*args, **kwargs)

    @property
    def TargetClass(self):
        if self._target_class:
            return self._target_class
        raise NotImplementedError()

    def get_object(self, object_id):
        return self.TargetClass.load(object_id)

    def to_internal_value(self, data):
        target = self.get_object(data)
        return {'target': target}


class PreprintRequestTargetRelationshipField(TargetRelationshipField):
    def to_representation(self, value):
        ret = super(TargetRelationshipField, self).to_representation(value)
        ret['data']['type'] = get_meta_type(
            PreprintRequestSerializer,
            self.context.get('request'),
        )
        return ret

class BaseActionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'trigger',
        'from_state',
        'to_state',
        'date_created',
        'date_modified',
        'target',
    ])

    id = ser.CharField(source='_id', read_only=True)

    trigger = ser.ChoiceField(choices=DefaultTriggers.choices())

    comment = ser.CharField(max_length=65535, required=False)

    from_state = ser.ChoiceField(choices=DefaultStates.choices(), read_only=True)
    to_state = ser.ChoiceField(choices=DefaultStates.choices(), read_only=True)

    date_created = ser.DateTimeField(source='created', read_only=True)
    date_modified = ser.DateTimeField(source='modified', read_only=True)
    auto = ser.BooleanField(read_only=True)

    creator = RelationshipField(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
        filter_key='creator__guids___id',
        always_embed=True,
    )

    links = LinksField(
        {
            'self': 'get_action_url',
        },
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
        permissions = validated_data.pop('permissions', '')
        visible = validated_data.pop('visible', '')

        try:
            if trigger == DefaultTriggers.ACCEPT.value:
                return target.run_accept(user=user, comment=comment, permissions=permissions, visible=visible)
            if trigger == DefaultTriggers.REJECT.value:
                return target.run_reject(user, comment)
            if trigger == DefaultTriggers.EDIT_COMMENT.value:
                return target.run_edit_comment(user, comment)
            if trigger == DefaultTriggers.SUBMIT.value:
                return target.run_submit(user)
        except InvalidTriggerError as e:
            # Invalid transition from the current state
            raise Conflict(str(e))
        else:
            raise JSONAPIAttributeException(attribute='trigger', detail='Invalid trigger.')

    class Meta:
        type_ = 'actions'
        abstract = True

class ReviewActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'review-actions'

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

    comment = HideIfProviderCommentsPrivate(ser.CharField(max_length=65535, required=False))
    trigger = ser.ChoiceField(choices=ReviewTriggers.choices())
    from_state = ser.ChoiceField(choices=ReviewStates.choices(), read_only=True)
    to_state = ser.ChoiceField(choices=ReviewStates.choices(), read_only=True)

    provider = RelationshipField(
        read_only=True,
        related_view='providers:preprint-providers:preprint-provider-detail',
        related_view_kwargs={'provider_id': '<target.provider._id>'},
        filter_key='target__provider___id',
    )

    creator = HideIfProviderCommentsAnonymous(RelationshipField(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
        filter_key='creator__guids___id',
        always_embed=True,
    ))

    target = TargetRelationshipField(
        target_class=Preprint,
        read_only=False,
        required=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<target._id>'},
        filter_key='target__guids___id',
    )

    def create(self, validated_data):
        trigger = validated_data.get('trigger')
        if trigger != ReviewTriggers.WITHDRAW.value:
            return super(ReviewActionSerializer, self).create(validated_data)
        user = validated_data.pop('user')
        target = validated_data.pop('target')
        comment = validated_data.pop('comment', '')
        try:
            return target.run_withdraw(user=user, comment=comment)
        except InvalidTriggerError as e:
            # Invalid transition from the current state
            raise Conflict(str(e))
        else:
            raise JSONAPIAttributeException(attribute='trigger', detail='Invalid trigger.')


class NodeRequestActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'node-request-actions'

    target = TargetRelationshipField(
        target_class=NodeRequest,
        read_only=False,
        required=True,
        related_view='requests:request-detail',
        related_view_kwargs={'request_id': '<target._id>'},
    )

    permissions = ser.ChoiceField(choices=permissions.API_CONTRIBUTOR_PERMISSIONS, required=False)
    visible = ser.BooleanField(default=True, required=False)


class PreprintRequestActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'preprint-request-actions'

    target = PreprintRequestTargetRelationshipField(
        target_class=PreprintRequest,
        read_only=False,
        required=True,
        related_view='requests:request-detail',
        related_view_kwargs={'request_id': '<target._id>'},
    )


class RegistrationActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'review-actions'

    permissions = ser.ChoiceField(choices=permissions.API_CONTRIBUTOR_PERMISSIONS, required=False)
    visible = ser.BooleanField(default=True, required=False)
    trigger = ser.ChoiceField(choices=RegistrationModerationTriggers.char_field_choices())

    target = TargetRelationshipField(
        target_class=Registration,
        read_only=False,
        required=True,
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<target._id>'},
        filter_key='target__guids___id',
    )

    def create(self, validated_data):
        trigger = validated_data.get('trigger')

        target = validated_data.pop('target')
        comment = validated_data.pop('comment', '')
        user = validated_data.pop('user')

        sanction = target.sanction

        try:
            if trigger in [RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name, RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name]:
                sanction.accept(user=user, comment=comment)
            elif trigger in [RegistrationModerationTriggers.REJECT_SUBMISSION.db_name, RegistrationModerationTriggers.REJECT_WITHDRAWAL.db_name]:
                sanction.reject(user=user, comment=comment)
            elif trigger == RegistrationModerationTriggers.FORCE_WITHDRAW.db_name:
                target.retract_registration(
                    user=user, justification=comment, moderator_initiated=True,
                )
            else:
                raise JSONAPIAttributeException(attribute='trigger', detail='Invalid trigger.')
        except InvalidTriggerError:
            # Invalid transition from the current state
            short_message = 'Operation not allowed at this time'
            long_message = f'This {trigger} is invalid for the current state of the registration'
            raise HTTPError(
                http_status.HTTP_400_BAD_REQUEST,
                data={'message_short': short_message, 'message_long': long_message},
            )
        except PermissionsError:
            raise PermissionDenied('You do not have permission to perform this trigger at this time')
        except ValueError:
            raise PermissionDenied('You do not have permission to perform this trigger at this time')
        except MachineError:
            raise PermissionDenied('You do not have permission to perform this trigger at this time')

        target.refresh_from_db()
        determined_trigger = target.actions.last().trigger

        if determined_trigger != trigger:
            short_message = 'Operation not allowed at this time'
            long_message = f'This {trigger} is invalid for the current state of the registration.'
            raise HTTPError(
                http_status.HTTP_400_BAD_REQUEST,
                data={'message_short': short_message, 'message_long': long_message},
            )

        return target.actions.last()
