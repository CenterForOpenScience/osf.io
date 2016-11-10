from rest_framework import serializers as ser
from rest_framework.exceptions import PermissionDenied, NotFound

from api.base.exceptions import RelationshipPostMakesNoChanges, NonDescendantNodeError
from api.base.serializers import (
    JSONAPISerializer, IDField, RelationshipField,
    JSONAPIRelationshipSerializer, LinksField, relationship_diff,
    DateByVersion,
)
from api.base.utils import absolute_reverse

from website.project.model import Node


class ViewOnlyLinkDetailSerializer(JSONAPISerializer):
    key = ser.CharField(read_only=True)
    id = IDField(source='_id', read_only=True)
    date_created = DateByVersion(read_only=True)
    anonymous = ser.BooleanField(required=False)
    name = ser.CharField(required=False)

    nodes = RelationshipField(
        related_view='view-only-links:view-only-link-nodes',
        related_view_kwargs={'link_id': '<_id>'},
        self_view='view-only-links:view-only-link-nodes-relationships',
        self_view_kwargs={'link_id': '<_id>'}
    )

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-view-only-link-detail',
            kwargs={
                'link_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )

    class Meta:
        type_ = 'view-only-links'


class VOLNode(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id')

    class Meta:
        type_ = 'nodes'


class ViewOnlyLinkNodesSerializer(ser.Serializer):
    data = ser.ListField(child=VOLNode())
    links = LinksField({
        'self': 'get_self_url',
    })

    def get_self_url(self, obj):
        return absolute_reverse(
            'view-only-links:view-only-link-nodes',
            kwargs={
                'link_id': obj['self']._id,
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )

    def make_instance_obj(self, obj):
        return {
            'data': obj.nodes,
            'self': obj
        }

    def get_nodes_to_add_remove(self, nodes, new_nodes):
        diff = relationship_diff(
            current_items={node._id: node for node in nodes},
            new_items={node['_id']: node for node in new_nodes}
        )

        nodes_to_add = []
        for node_id in diff['add']:
            node = Node.load(node_id)
            if not node:
                raise NotFound
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def get_eligible_nodes(self, nodes):
        return [
            descendant
            for node in nodes
            for descendant in node.get_descendants_recursive()
        ]

    def create(self, validated_data):

        instance = self.context['view'].get_object()
        view_only_link = instance['self']
        nodes = instance['data']
        user = self.context['request'].user
        new_nodes = validated_data['data']

        add, remove = self.get_nodes_to_add_remove(
            nodes=nodes,
            new_nodes=new_nodes
        )

        if not len(add):
            raise RelationshipPostMakesNoChanges

        eligible_nodes = self.get_eligible_nodes(nodes)

        for node in add:
            if not node.has_permission(user, 'admin'):
                raise PermissionDenied
            if node not in eligible_nodes:
                raise NonDescendantNodeError(node_id=node._id)
            view_only_link.nodes.append(node)

        view_only_link.save()

        return self.make_instance_obj(view_only_link)

    def update(self, instance, validated_data):
        view_only_link = instance['self']
        nodes = instance['data']
        user = self.context['request'].user
        new_nodes = validated_data['data']

        add, remove = self.get_nodes_to_add_remove(
            nodes=nodes,
            new_nodes=new_nodes
        )

        for node in remove:
            if not node.has_permission(user, 'admin'):
                raise PermissionDenied
            view_only_link.nodes.remove(node)
        view_only_link.save()

        nodes = [Node.load(node) for node in view_only_link.nodes]
        eligible_nodes = self.get_eligible_nodes(nodes)

        for node in add:
            if not node.has_permission(user, 'admin'):
                raise PermissionDenied
            if node not in eligible_nodes:
                raise NonDescendantNodeError(node_id=node._id)
            view_only_link.nodes.append(node)
        view_only_link.save()

        return self.make_instance_obj(view_only_link)

    class Meta:
        type_ = 'nodes'
