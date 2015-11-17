from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer,
    RelationshipField
)


class NodeLogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action', 'date'])

    id = ser.CharField(read_only=True, source='_id')
    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(read_only=True)

    class Meta:
        type_ = 'logs'

    nodes = RelationshipField(
        related_view='logs:log-nodes',
        related_view_kwargs={'log_id': '<pk>'},
    )
    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
    )
