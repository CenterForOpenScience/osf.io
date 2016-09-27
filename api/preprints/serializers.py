from modularodm import Q
from modularodm.exceptions import ValidationValueError
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, IDField, JSONAPIListField,
    LinksField, RelationshipField
)
from api.base.utils import absolute_reverse, get_user_auth
from api.taxonomies.serializers import TaxonomyField
from framework.exceptions import PermissionsError
from website.util import permissions
from website.project import signals as project_signals
from website.models import StoredFileNode, PreprintService, PreprintProvider, Node


class PrimaryFileRelationshipField(RelationshipField):
    def get_object(self, file_id):
        return StoredFileNode.load(file_id)

    def to_internal_value(self, data):
        file = self.get_object(data)
        return {'primary_file': file}

class NodeRelationshipField(RelationshipField):
    def get_object(self, node_id):
        return Node.load(node_id)

    def to_internal_value(self, data):
        node = self.get_object(data)
        return {'node': node}

class PreprintProviderRelationshipField(RelationshipField):
    def get_object(self, node_id):
        return PreprintProvider.load(node_id)

    def to_internal_value(self, data):
        provider = self.get_object(data)
        return {'provider': provider}

class PreprintSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'date_created',
        'date_published',
        'subjects',
        'doi',
        'provider',
        'is_published',
    ])

    id = IDField(source='_id', required=False)
    subjects = JSONAPIListField(child=JSONAPIListField(child=TaxonomyField()), required=False)
    provider = ser.CharField(required=False)
    date_created = ser.DateTimeField(read_only=True)
    date_published = ser.DateTimeField(read_only=True)
    doi = ser.CharField(source='preprint_article_doi', required=False)
    is_published = ser.BooleanField(required=False)

    node = NodeRelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
        read_only=False
    )

    provider = PreprintProviderRelationshipField(
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False
    )

    primary_file = PrimaryFileRelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<preprint_file._id>'},
        lookup_url_kwarg='file_id',
        read_only=False
    )

    links = LinksField(
        {
            'self': 'get_preprint_url',
            'html': 'get_absolute_html_url',
            'doi': 'get_doi_url'
        }
    )

    class Meta:
        type_ = 'preprints'

    def get_preprint_url(self, obj):
        return absolute_reverse('preprints:preprint-detail', kwargs={'preprint_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)

    def get_doi_url(self, obj):
        return 'https://dx.doi.org/{}'.format(obj.preprint_article_doi) if obj.preprint_article_doi else None

    def create(self, validated_data):
        node = Node.load(validated_data.pop('node', None))
        if not node:
            raise exceptions.NotFound('Unable to find Node with specified id.')

        auth = get_user_auth(self.context['request'])
        if not node.has_permission(auth.user, permissions.ADMIN):
            raise exceptions.PermissionDenied

        primary_file = validated_data.pop('primary_file', None)
        if not primary_file:
            raise exceptions.ValidationError(detail='You must specify a primary_file to create a preprint.')

        provider = validated_data.pop('provider', None)
        if not provider:
            raise exceptions.ValidationError(detail='You must specify a provider to create a preprint.')

        if PreprintService.find(Q('node', 'eq', node) & Q('provider', 'eq', provider)).count():
            raise exceptions.ValidationError('Only one preprint per provider can be submitted for a node.')

        preprint = PreprintService(node=node, provider=provider)
        self.set_field(preprint.set_preprint_file, primary_file, auth, save=True)

        return preprint

    def update(self, preprint, validated_data):
        from website.models import Node
        assert isinstance(preprint, PreprintService), 'You must specify a valid preprint to be updated'
        assert isinstance(preprint.node, Node), 'You must specify a preprint with a valid node to be updated.'

        auth = get_user_auth(self.context['request'])
        if not preprint.node.has_permission(auth.user, 'admin'):
            raise exceptions.PermissionDenied(detail='User must be an admin to update a preprint.')

        save_node = False
        save_preprint = False
        recently_published = False

        primary_file = validated_data.pop('primary_file', None)
        if primary_file:
            self.set_field(preprint.set_preprint_file, primary_file, auth)
            save_node = True
        subjects = validated_data.pop('subjects', None)
        if subjects:
            self.set_field(preprint.set_preprint_subjects, subjects, auth)
            save_preprint = True

        if 'doi' in validated_data:
            preprint.node.preprint_article_doi = validated_data['doi']
            save_node = True

        published = validated_data.pop('is_published', None)
        if published is not None:
            self.set_field(preprint.set_published, published, auth)
            save_preprint = True
            recently_published = published

        if save_node:
            try:
                preprint.node.save()
            except ValidationValueError as e:
                # Raised from invalid DOI
                raise exceptions.ValidationError(detail=e.message)

        if save_preprint:
            preprint.save()

        # Send preprint confirmation email signal to new authors on preprint! -- only when published
        # TODO: Some more thought might be required on this; preprints made from existing
        # nodes will send emails making it seem like a new node.
        if recently_published:
            for author in preprint.node.contributors:
                if author != auth.user:
                    project_signals.contributor_added.send(preprint.node, contributor=author, auth=auth, email_template='preprint')

        return preprint

    def set_field(self, func, val, auth, save=False):
        try:
            func(val, auth, save=save)
        except PermissionsError:
            raise exceptions.PermissionDenied('Not authorized to update this node.')
        except ValueError as e:
            raise exceptions.ValidationError(detail=e.message)
