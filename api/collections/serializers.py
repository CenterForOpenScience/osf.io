from django.db import IntegrityError
from rest_framework import serializers as ser

from osf.models import AbstractNode, Node, Collection, Registration
from osf.exceptions import ValidationError
from api.base.serializers import LinksField, RelationshipField, LinkedNodesRelationshipSerializer, LinkedRegistrationsRelationshipSerializer
from api.base.serializers import JSONAPISerializer, IDField, TypeField, VersionedDateTimeField
from api.base.exceptions import InvalidModelValueError, RelationshipPostMakesNoChanges
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
    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)
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
        auth = get_user_auth(self.context['request'])
        return Node.objects.filter(guids__in=obj.guid_links.all(), is_deleted=False).can_view(user=auth.user, private_link=auth.private_link).count()

    def get_registration_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        return Registration.objects.filter(guids__in=obj.guid_links.all(), is_deleted=False).can_view(user=auth.user, private_link=auth.private_link).count()

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

    def update(self, collection, validated_data):
        """Update instance with the validated data.
        """
        assert isinstance(collection, Collection), 'collection must be a Collection'
        if validated_data:
            for key, value in validated_data.iteritems():
                if key == 'title' and collection.is_bookmark_collection:
                    raise InvalidModelValueError('Bookmark collections cannot be renamed.')
                setattr(collection, key, value)
        try:
            collection.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])
        return collection


class CollectionDetailSerializer(CollectionSerializer):
    """
    Overrides CollectionSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class CollectionNodeLinkSerializer(NodeLinksSerializer):
    target_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<guid.referent._id>'},
        always_embed=True
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'collections:node-pointer-detail',
            kwargs={
                'collection_id': self.context['request'].parser_context['kwargs']['collection_id'],
                'node_link_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )

    # Override NodeLinksSerializer
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        collection = self.context['view'].get_collection()
        target_node_id = validated_data['_id']
        pointer_node = AbstractNode.load(target_node_id)
        if not pointer_node:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' not found.'.format(target_node_id)
            )
        try:
            pointer = collection.collect_object(pointer_node, user)
        except ValidationError:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' already pointed to by \'{}\'.'.format(target_node_id, collection._id)
            )
        return pointer

class CollectedAbstractNodeRelationshipSerializer(object):
    _abstract_node_subclass = None

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {'data':
            list(self._abstract_node_subclass.objects.filter(
                guids__in=obj.guid_links.all(), is_deleted=False
            )),
            'self': obj}

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        for pointer in remove:
            collection.remove_object(pointer)
        for node in add:
            collection.collect_object(node, auth.user)

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        if not len(add):
            raise RelationshipPostMakesNoChanges

        for node in add:
            try:
                collection.collect_object(node, auth.user)
            except ValidationError as e:
                raise InvalidModelValueError(
                    source={'pointer': '/data/relationships/node_links/data/id'},
                    detail='Target Node {} generated error: {}.'.format(node._id, e.message)
                )

        return self.make_instance_obj(collection)

class CollectedNodeRelationshipSerializer(CollectedAbstractNodeRelationshipSerializer, LinkedNodesRelationshipSerializer):
    _abstract_node_subclass = Node

class CollectedRegistrationsRelationshipSerializer(CollectedAbstractNodeRelationshipSerializer, LinkedRegistrationsRelationshipSerializer):
    _abstract_node_subclass = Registration
