from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, IDField, RelationshipField
)
from api.base.utils import absolute_reverse


class ViewOnlyLinkDetailSerializer(JSONAPISerializer):
    key = ser.CharField(read_only=True)
    id = IDField(source='_id', read_only=True)
    date_created = ser.DateTimeField(read_only=True)
    anonymous = ser.BooleanField(required=False)
    name = ser.CharField(required=False)

    nodes = RelationshipField(
        related_view='view_only_links:view-only-link-nodes',
        related_view_kwargs={'link_id': '<_id>'}
    )

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-view-only-link-detail',
            kwargs={
                'key': obj.key
            }
        )

    class Meta:
        type_ = 'view_only_links'
