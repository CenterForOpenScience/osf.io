from rest_framework import serializers as ser
from rest_framework import exceptions
from modularodm.exceptions import ValidationValueError

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from website.models import Node
from api.base.serializers import LinksField, JSONAPIHyperlinkedIdentityField, DevOnly
from api.base.serializers import JSONAPISerializer, IDField, TypeField
from api.base.exceptions import InvalidModelValueError
from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeLinksSerializer


class CollectionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'title',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    title = ser.CharField(required=True)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    links = LinksField({'html': 'get_absolute_url'})

    node_links = DevOnly(JSONAPIHyperlinkedIdentityField(view_name='collections:node-pointers', lookup_field='pk', link_type='related',
                                                  lookup_url_kwarg='collection_id', meta={'count': 'get_node_links_count'}))
    # TODO: Add a self link to this when it's available
    linked_nodes = DevOnly(JSONAPIHyperlinkedIdentityField(view_name='collections:linked-nodes', lookup_field='pk', link_type='related',
                                                  lookup_url_kwarg='collection_id', meta={'count': 'get_node_links_count'}))
    class Meta:
        type_ = 'collections'

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_user_auth(self, request):
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        return auth

    def get_node_links_count(self, obj):
        return len(obj.nodes_pointer)

    def create(self, validated_data):
        node = Node(**validated_data)
        try:
            node.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)
        return node

    def update(self, node, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(node, Node), 'collection must be a Node'
        auth = self.get_user_auth(self.context['request'])

        if validated_data:
            try:
                node.update(validated_data, auth=auth)
            except ValidationValueError as e:
                raise InvalidModelValueError(detail=e.message)
            except PermissionsError:
                raise exceptions.PermissionDenied

        return node


class CollectionDetailSerializer(CollectionSerializer):
    """
    Overrides CollectionSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class CollectionNodeLinkSerializer(NodeLinksSerializer):
    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['collection_id']
        return absolute_reverse(
            'collections:node-pointer-detail',
            kwargs={
                'collection_id': node_id,
                'node_link_id': obj._id
            }
        )
