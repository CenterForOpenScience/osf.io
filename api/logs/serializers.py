from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    RelationshipField,
    RestrictedDictSerializer,
    LinksField)
from api.base.utils import absolute_reverse


class NodeLogIdentifiersSerializer(RestrictedDictSerializer):

    doi = ser.CharField(read_only=True)
    ark = ser.CharField(read_only=True)


class NodeLogFileParamsSerializer(RestrictedDictSerializer):

    materialized = ser.CharField(read_only=True)
    url = ser.URLField(read_only=True)
    addon = ser.CharField(read_only=True)
    node_url = ser.URLField(read_only=True, source='node.url')
    node_title = ser.URLField(read_only=True, source='node.title')


class NodeLogParamsSerializer(RestrictedDictSerializer):

    tags = ser.CharField(read_only=True)
    title_original = ser.CharField(read_only=True)
    title_new = ser.CharField(read_only=True)
    updated_fields = ser.ListField(read_only=True)
    addon = ser.CharField(read_only=True)
    source = NodeLogFileParamsSerializer(read_only=True)
    target = NodeLogFileParamsSerializer(read_only=True)
    identifiers = NodeLogIdentifiersSerializer(read_only=True)


class NodeLogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action', 'date'])

    id = ser.CharField(read_only=True, source='_id')
    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(read_only=True)
    params = NodeLogParamsSerializer(read_only=True)
    links = LinksField({'self': 'get_absolute_url'})

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
    # This would be a node_link, except that data isn't stored in the node log params
    linked_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<params.pointer.id>'}
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'logs:log-detail',
            kwargs={
                'log_id': obj._id,
            }
        )
