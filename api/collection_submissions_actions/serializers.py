from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, EnumField
from api.actions.serializers import TargetRelationshipField, LinksField
from osf.models import CollectionSubmission
from osf.utils.workflows import ApprovalStates, CollectionSubmissionsTriggers
from rest_framework import serializers as ser

from api.base.serializers import (
    RelationshipField,
)


class CollectionSubmissionActionSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'collection-submissions-actions'

    id = ser.CharField(source='_id', read_only=True)

    trigger = EnumField(CollectionSubmissionsTriggers)
    from_state = EnumField(ApprovalStates)
    to_state = EnumField(ApprovalStates)
    comment = ser.CharField(max_length=65535, required=False, allow_blank=True, allow_null=True)

    collection = RelationshipField(
        related_view='collections:collection-detail',
        related_view_kwargs={'collection_id': '<target.collection._id>'},
    )

    creator = RelationshipField(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    target = TargetRelationshipField(
        target_class=CollectionSubmission,
        read_only=False,
        required=True,
        related_view='collections:collected-metadata-detail',
        related_view_kwargs={
            'collection_id': '<target.collection._id>',
            'cgm_id': '<target.guid._id>',
        },
        filter_key='target__guids___id',
    )

    links = LinksField(
        {
            'self': 'get_action_url',
        },
    )

    def get_absolute_url(self, obj):
        return self.get_action_url(obj)

    def get_action_url(self, obj):
        return absolute_reverse(
            'actions:action-detail',
            kwargs={
                'action_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )
