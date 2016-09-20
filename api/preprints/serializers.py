from modularodm.exceptions import ValidationValueError
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, IDField, JSONAPIListField, LinksField,
    RelationshipField, JSONAPIRelationshipSerializer, relationship_diff
)
from api.base.exceptions import Conflict, RelationshipPostMakesNoChanges
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import NodeTagField
from api.taxonomies.serializers import TaxonomyField
from framework.exceptions import PermissionsError
from website.util import permissions
from website.project import signals as project_signals
from website.models import StoredFileNode, PreprintProvider, Node


class PrimaryFileRelationshipField(RelationshipField):
    def get_object(self, file_id):
        return StoredFileNode.load(file_id)

    def to_internal_value(self, data):
        file = self.get_object(data)
        return {'primary_file': file}


class PreprintSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'title',
        'tags',
        'date_created',
        'date_modified',
        'contributors',
        'subjects',
        'doi'
    ])

    title = ser.CharField(required=False)
    subjects = JSONAPIListField(child=TaxonomyField(), required=False, source='preprint_subjects')
    provider = ser.CharField(source='preprint_provider', required=False)
    date_created = ser.DateTimeField(read_only=True, source='preprint_created')
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)
    doi = ser.CharField(source='preprint_doi', required=False)
    csl = ser.DictField(read_only=True)

    primary_file = PrimaryFileRelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<preprint_file._id>'},
        lookup_url_kwarg='file_id',
        read_only=False
    )

    files = RelationshipField(
        related_view='nodes:node-providers',
        related_view_kwargs={'node_id': '<pk>'}
    )

    providers = RelationshipField(
        related_view='preprints:preprint-preprint_providers',
        related_view_kwargs={'node_id': '<pk>'},
        self_view='preprints:preprint-relationships-preprint_providers',
        self_view_kwargs={'node_id': '<pk>'}
    )

    links = LinksField(
        {
            'self': 'get_preprint_url',
            'html': 'get_absolute_html_url',
            'doi': 'get_doi_url'
        }
    )

    contributors = RelationshipField(
        related_view='nodes:node-contributors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'},
    )

    class Meta:
        type_ = 'preprints'

    def get_preprint_url(self, obj):
        return absolute_reverse('preprints:preprint-detail', kwargs={'node_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)

    def get_doi_url(self, obj):
        return 'https://dx.doi.org/{}'.format(obj.preprint_doi) if obj.preprint_doi else None

    def create(self, validated_data):
        node = Node.load(validated_data.pop('_id', None))
        if not node:
            raise exceptions.NotFound('Unable to find Node with specified id.')

        auth = get_user_auth(self.context['request'])
        if not node.has_permission(auth.user, permissions.ADMIN):
            raise exceptions.PermissionDenied

        if node.is_preprint:
            raise Conflict('This node already stored as a preprint, use the update method instead.')

        primary_file = validated_data.pop('primary_file', None)
        if not primary_file:
            raise exceptions.ValidationError(detail='You must specify a primary_file to create a preprint.')

        self.set_node_field(node.set_preprint_file, primary_file, auth)

        subjects = validated_data.pop('preprint_subjects', None)
        if not subjects:
            raise exceptions.ValidationError(detail='You must specify at least one subject to create a preprint.')

        self.set_node_field(node.set_preprint_subjects, subjects, auth)

        tags = validated_data.pop('tags', None)
        if tags:
            for tag in tags:
                node.add_tag(tag, auth, save=False, log=False)

        for key, value in validated_data.iteritems():
            setattr(node, key, value)
        try:
            node.save()
        except ValidationValueError as e:
            raise exceptions.ValidationError(detail=e.message)

        # Send preprint confirmation email signal to new authors on preprint!
        for author in node.contributors:
            if author != auth.user:
                project_signals.contributor_added.send(node, contributor=author, auth=auth, email_template='preprint')

        return node

    def update(self, node, validated_data):
        from website.models import Node
        assert isinstance(node, Node), 'You must specify a valid node to be updated.'
        auth = get_user_auth(self.context['request'])
        primary_file = validated_data.pop('primary_file', None)
        if primary_file:
            self.set_node_field(node.set_preprint_file, primary_file, auth)
        subjects = validated_data.pop('preprint_subjects', None)
        if subjects:
            self.set_node_field(node.set_preprint_subjects, subjects, auth)

        old_tags = set([tag._id for tag in node.tags])
        if 'tags' in validated_data:
            current_tags = set(validated_data.pop('tags', []))
        elif self.partial:
            current_tags = set(old_tags)
        else:
            current_tags = set()

        for new_tag in (current_tags - old_tags):
            node.add_tag(new_tag, auth=auth)
        for deleted_tag in (old_tags - current_tags):
            node.remove_tag(deleted_tag, auth=auth)

        for key, value in validated_data.iteritems():
            setattr(node, key, value)
        try:
            node.save()
        except ValidationValueError as e:
            raise exceptions.ValidationError(detail=e.message)
        return node

    def set_node_field(self, func, val, auth):
        try:
            func(val, auth, save=False)
        except PermissionsError:
            raise exceptions.PermissionDenied('Not authorized to update this node.')
        except ValueError as e:
            raise exceptions.ValidationError(detail=e.message)


class PreprintProviderRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=True, allow_null=False)
    class Meta:
        type_ = 'preprint_providers'


class PreprintPreprintProvidersRelationshipSerializer(ser.Serializer):
    data = ser.ListField(child=PreprintProviderRelated())

    class Meta:
        type_ = 'preprint_providers'

    def get_providers_to_add_remove(self, providers, new_providers):
        diff = relationship_diff(
            current_items={provider._id: provider for provider in providers},
            new_items={provider['_id']: provider for provider in new_providers}
        )

        providers_to_add = []
        for provider_id in diff['add']:
            provider = PreprintProvider.load(provider_id)
            if not provider:
                raise exceptions.NotFound(detail='PreprintProvider with id "{}" was not found'.format(provider_id))
            providers_to_add.append(provider)

        return providers_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        return {
            'data': obj.preprint_providers,
            'self': obj
        }

    def update(self, instance, validated_data):
        node = instance['self']
        user = self.context['request'].user

        add, remove = self.get_providers_to_add_remove(
            providers=instance['data'],
            new_providers=validated_data['data']
        )

        if not node.has_permission(user, 'admin'):
            raise exceptions.PermissionDenied(detail='User must be an admin to update the PreprintProvider relationship.')

        for provider in remove:
            node.remove_preprint_provider(provider, user)
        for provider in add:
            node.add_preprint_provider(provider, user)

        node.save()

        return self.make_instance_obj(node)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        user = self.context['request'].user
        node = instance['self']

        if not node.has_permission(user, 'admin'):
            raise exceptions.PermissionDenied(detail='User must be an admin to create a PreprintProvider relationship.')

        add, remove = self.get_providers_to_add_remove(
            providers=instance['data'],
            new_providers=validated_data['data']
        )
        if not len(add):
            raise RelationshipPostMakesNoChanges

        for provider in add:
            node.add_preprint_provider(provider, user)

        node.save()

        return self.make_instance_obj(node)
