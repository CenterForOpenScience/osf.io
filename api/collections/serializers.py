from django.db import IntegrityError
from rest_framework import serializers as ser
from rest_framework import exceptions
from framework.exceptions import PermissionsError

from website.models import Node
from osf.models import Collection
from osf.exceptions import ValidationError
from api.base.serializers import LinksField, RelationshipField
from api.base.serializers import JSONAPISerializer, IDField, TypeField, DateByVersion
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
    date_created = DateByVersion(read_only=True)
    date_modified = DateByVersion(read_only=True)
    bookmarks = ser.BooleanField(read_only=False, default=False, source='is_bookmark_collection')

    links = LinksField({})

    node_links = RelationshipField(
        related_view='collections:node-pointers',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'}
    )

    # TODO: Add a self link to this when it's available
    linked_nodes = RelationshipField(
        related_view='collections:linked-nodes',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='collections:collection-node-pointer-relationship',
        self_view_kwargs={'collection_id': '<_id>'}
    )

    linked_registrations = RelationshipField(
        related_view='collections:linked-registrations',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_registration_links_count'},
        self_view='collections:collection-registration-pointer-relationship',
        self_view_kwargs={'collection_id': '<_id>'}
    )

    class Meta:
        type_ = 'collections'

    def get_absolute_url(self, obj):
        return absolute_reverse('collections:collection-detail', kwargs={
            'collection_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_node_links_count(self, obj):
        count = 0
        auth = get_user_auth(self.context['request'])
        for pointer in obj.linked_nodes.filter(is_deleted=False, type='osf.node'):
            if pointer.can_view(auth):
                count += 1
        return count

    def get_registration_links_count(self, obj):
        count = 0
        auth = get_user_auth(self.context['request'])
        for pointer in obj.linked_nodes.filter(is_deleted=False, type='osf.registration'):
            if pointer.can_view(auth):
                count += 1
        return count

    def create(self, validated_data):
        node = Collection(**validated_data)
        node.category = ''
        try:
            node.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])
        except IntegrityError:
            raise ser.ValidationError('Each user cannot have more than one Bookmark collection.')
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
            except ValidationError as e:
                raise InvalidModelValueError(detail=e.messages[0])
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
        return absolute_reverse(
            'collections:node-pointer-detail',
            kwargs={
                'collection_id': self.context['request'].parser_context['kwargs']['collection_id'],
                'node_link_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )
