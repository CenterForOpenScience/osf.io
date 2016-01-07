from rest_framework import serializers as ser
from rest_framework import exceptions
from modularodm import Q
from modularodm.exceptions import ValidationValueError
from framework.exceptions import PermissionsError

from website.models import Node, Pointer
from api.base.serializers import LinksField, RelationshipField, DevOnly, RelationshipResourceIdObjectSerializer
from api.base.serializers import JSONAPISerializer, IDField, TypeField, relationship_diff
from api.base.exceptions import InvalidModelValueError
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import NodeLinksSerializer


class CollectionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'title',
        'date_created',
        'date_modified',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    title = ser.CharField(required=True)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    links = LinksField({})

    node_links = DevOnly(RelationshipField(
        related_view='collections:node-pointers',
        related_view_kwargs={'collection_id': '<pk>'},
        related_meta={'count': 'get_node_links_count'}
    ))

    # TODO: Add a self link to this when it's available
    linked_nodes = DevOnly(RelationshipField(
        related_view='collections:linked-nodes',
        related_view_kwargs={'collection_id': '<pk>'},
        related_meta={'count': 'get_node_links_count'}
    ))

    class Meta:
        type_ = 'collections'

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_node_links_count(self, obj):
        return len(obj.nodes_pointer)

    def create(self, validated_data):
        node = Node(**validated_data)
        node.is_folder = True
        node.category = ''
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
        auth = get_user_auth(self.context['request'])

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


class LinkedNode(RelationshipResourceIdObjectSerializer):
    class Meta:
        type_ = 'linked_nodes'


class CollectionLinkedNodesRelationshipSerializer(ser.Serializer):

    data = ser.ListField(child=LinkedNode())
    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return obj['self'].linked_nodes_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_nodes_related_url

    class Meta:
        type_ = 'linked_nodes'

    def get_pointers_to_add_remove(self, pointers, new_pointers):
        diff = relationship_diff(
            current_items={pointer.node._id: pointer for pointer in pointers},
            new_items={val['node']['_id']: val for val in new_pointers}
        )

        nodes_to_add = []
        for node_id in diff['add'].keys():
            node = Node.load(node_id)
            if not node:
                raise exceptions.NotFound
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {'data': [
            pointer for pointer in
            obj.nodes_pointer
            if not pointer.node.is_deleted and not pointer.node.is_folder
        ], 'self': obj}

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(
                pointers=instance['data'],
                new_pointers=validated_data['data']
        )

        for pointer in remove:
            collection.rm_pointer(pointer, auth)
        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(
                pointers=instance['data'],
                new_pointers=validated_data['data']
        )

        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)
