from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, JSONAPIListField, IDField, RelationshipField
)
from api.nodes.serializers import NodeVOL


class ViewOnlyLinkDetailSerializer(JSONAPISerializer):
    """
    Document pls.
    """
    key = ser.CharField(read_only=True)
    id = IDField(source='_id', read_only=True)
    date_created = ser.DateTimeField(read_only=True)
    nodes = JSONAPIListField(child=NodeVOL(), required=False)
    anonymous = ser.BooleanField(required=False)
    name = ser.CharField(required=False)

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    class Meta:
        type_ = 'view_only_links'
