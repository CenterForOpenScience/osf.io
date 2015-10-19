from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer,
    JSONAPIHyperlinkedIdentityField
)

class NodeLogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action', 'date'])

    id = ser.CharField(read_only=True, source='_id')
    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(read_only=True)

    class Meta:
        type_ = 'logs'

    nodes = JSONAPIHyperlinkedIdentityField(
        view_name='logs:log-nodes',
        lookup_field='pk',
        lookup_url_kwarg='log_id'
    )
    user = JSONAPIHyperlinkedIdentityField(
        view_name='users:user-detail',
        lookup_field='user._id',
        lookup_url_kwarg='user_id'
    )
