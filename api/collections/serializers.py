from django.db import IntegrityError
from rest_framework import exceptions
from rest_framework import serializers as ser

from osf.models import AbstractNode, Node, Collection, Guid, Registration, CollectionProvider
from osf.exceptions import ValidationError, NodeStateError
from api.base.serializers import LinksField, RelationshipField, LinkedNodesRelationshipSerializer, LinkedRegistrationsRelationshipSerializer, LinkedPreprintsRelationshipSerializer
from api.base.serializers import JSONAPISerializer, IDField, TypeField, VersionedDateTimeField
from api.base.exceptions import InvalidModelValueError, RelationshipPostMakesNoChanges
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import NodeLinksSerializer
from api.taxonomies.serializers import TaxonomizableSerializerMixin
from framework.exceptions import PermissionsError
from osf.utils.permissions import WRITE


class CollectionProviderRelationshipField(RelationshipField):
    def get_object(self, provider_id):
        return CollectionProvider.load(provider_id)

    def to_internal_value(self, data):
        provider = self.get_object(data)
        return {'provider': provider}

class GuidRelationshipField(RelationshipField):
    def get_object(self, _id):
        return Guid.load(_id)

    def to_internal_value(self, data):
        guid = self.get_object(data)
        return {'guid': guid}


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
    is_promoted = ser.BooleanField(read_only=True, default=False)
    is_public = ser.BooleanField(read_only=False, default=False)
    status_choices = ser.ListField(
        child=ser.CharField(max_length=127),
        default=list(),
    )
    collected_type_choices = ser.ListField(
        child=ser.CharField(max_length=127),
        default=list(),
    )
    volume_choices = ser.ListField(
        child=ser.CharField(max_length=127),
        default=list(),
    )
    issue_choices = ser.ListField(
        child=ser.CharField(max_length=127),
        default=list(),
    )
    program_area_choices = ser.ListField(
        child=ser.CharField(max_length=127),
        default=list(),
    )

    links = LinksField({})

    provider = CollectionProviderRelationshipField(
        related_view='providers:collection-providers:collection-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=True,
    )

    node_links = RelationshipField(
        related_view='collections:node-pointers',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
    )

    # TODO: Add a self link to this when it's available
    linked_nodes = RelationshipField(
        related_view='collections:linked-nodes',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='collections:collection-node-pointer-relationship',
        self_view_kwargs={'collection_id': '<_id>'},
    )

    linked_registrations = RelationshipField(
        related_view='collections:linked-registrations',
        related_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_registration_links_count'},
        self_view='collections:collection-registration-pointer-relationship',
        self_view_kwargs={'collection_id': '<_id>'},
    )

    linked_preprints = RelationshipField(
        related_view='collections:linked-preprints',
        related_view_kwargs={'collection_id': '<_id>'},
        self_view='collections:collection-preprint-pointer-relationship',
        self_view_kwargs={'collection_id': '<_id>'},
        related_meta={'count': 'get_preprint_links_count'},
    )

    class Meta:
        type_ = 'collections'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'collections:collection-detail', kwargs={
                'collection_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_node_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        node_ids = obj.guid_links.all().values_list('_id', flat=True)
        return Node.objects.filter(guids___id__in=node_ids, is_deleted=False).can_view(user=auth.user, private_link=auth.private_link).count()

    def get_registration_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        registration_ids = obj.guid_links.all().values_list('_id', flat=True)
        return Registration.objects.filter(guids___id__in=registration_ids, is_deleted=False).can_view(user=auth.user, private_link=auth.private_link).count()

    def get_preprint_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        return self.context['view'].collection_preprints(obj, auth.user).count()

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
            for key, value in validated_data.items():
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


class CollectionSubmissionSerializer(TaxonomizableSerializerMixin, JSONAPISerializer):

    class Meta:
        type_ = 'collected-metadata'

    filterable_fields = frozenset([
        'id',
        'collected_type',
        'date_created',
        'date_modified',
        'subjects',
        'status',
    ])
    id = IDField(source='guid._id', read_only=True)
    type = TypeField()

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )
    collection = RelationshipField(
        related_view='collections:collection-detail',
        related_view_kwargs={'collection_id': '<collection._id>'},
    )
    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        always_embed=True,
    )
    collected_type = ser.CharField(required=False)
    status = ser.CharField(required=False)
    volume = ser.CharField(required=False)
    issue = ser.CharField(required=False)
    program_area = ser.CharField(required=False)

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'collected-metadata:collected-metadata-detail',
            kwargs={
                'collection_id': obj.collection._id,
                'cgm_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def update(self, obj, validated_data):
        if validated_data and 'subjects' in validated_data:
            auth = get_user_auth(self.context['request'])
            subjects = validated_data.pop('subjects', None)
            try:
                obj.set_subjects(subjects, auth)
            except PermissionsError as e:
                raise exceptions.PermissionDenied(detail=str(e))
            except (ValueError, NodeStateError) as e:
                raise exceptions.ValidationError(detail=str(e))
        if 'status' in validated_data:
            obj.status = validated_data.pop('status')
        if 'collected_type' in validated_data:
            obj.collected_type = validated_data.pop('collected_type')
        obj.save()
        return obj

class CollectionSubmissionCreateSerializer(CollectionSubmissionSerializer):
    # Makes guid writeable only on create
    guid = GuidRelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        always_embed=True,
        read_only=False,
        required=True,
    )

    def create(self, validated_data):
        subjects = validated_data.pop('subjects', None)
        collection = validated_data.pop('collection', None)
        creator = validated_data.pop('creator', None)
        guid = validated_data.pop('guid')
        if not collection:
            raise exceptions.ValidationError('"collection" must be specified.')
        if not creator:
            raise exceptions.ValidationError('"creator" must be specified.')
        if not (creator.has_perm('write_collection', collection) or (hasattr(guid.referent, 'has_permission') and guid.referent.has_permission(creator, WRITE))):
            raise exceptions.PermissionDenied('Must have write permission on either collection or collected object to collect.')
        try:
            obj = collection.collect_object(guid.referent, creator, **validated_data)
        except ValidationError as e:
            raise InvalidModelValueError(e.message)
        if subjects:
            auth = get_user_auth(self.context['request'])
            try:
                obj.set_subjects(subjects, auth)
            except PermissionsError as e:
                raise exceptions.PermissionDenied(detail=str(e))
            except (ValueError, NodeStateError) as e:
                raise exceptions.ValidationError(detail=str(e))
        return obj


class CollectionNodeLinkSerializer(NodeLinksSerializer):
    target_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<guid.referent._id>'},
        always_embed=True,
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'collections:node-pointer-detail',
            kwargs={
                'collection_id': self.context['request'].parser_context['kwargs']['collection_id'],
                'node_link_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
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
                detail='Target Node \'{}\' not found.'.format(target_node_id),
            )
        try:
            pointer = collection.collect_object(pointer_node, user)
        except ValidationError:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' already pointed to by \'{}\'.'.format(target_node_id, collection._id),
            )
        return pointer

class CollectedAbstractNodeRelationshipSerializer(object):
    _abstract_node_subclass = None

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data':
            list(self._abstract_node_subclass.objects.filter(
                guids__in=obj.guid_links.all(), is_deleted=False,
            )),
            'self': obj,
        }

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
                    detail='Target Node {} generated error: {}.'.format(node._id, e.message),
                )

        return self.make_instance_obj(collection)

class CollectedNodeRelationshipSerializer(CollectedAbstractNodeRelationshipSerializer, LinkedNodesRelationshipSerializer):
    _abstract_node_subclass = Node

class CollectedRegistrationsRelationshipSerializer(CollectedAbstractNodeRelationshipSerializer, LinkedRegistrationsRelationshipSerializer):
    _abstract_node_subclass = Registration

class CollectedPreprintsRelationshipSerializer(CollectedAbstractNodeRelationshipSerializer, LinkedPreprintsRelationshipSerializer):

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data':
                list(self.context['view'].collection_preprints(obj, user=get_user_auth(self.context['request']).user)),
            'self': obj,
        }

    class Meta:
        type_ = 'linked_preprints'
