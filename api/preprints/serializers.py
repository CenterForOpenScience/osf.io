from modularodm.exceptions import ValidationError
from modularodm import Q
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.exceptions import Conflict
from api.base.serializers import (
    JSONAPISerializer, IDField, JSONAPIListField,
    LinksField, RelationshipField, DateByVersion,
)
from api.base.utils import absolute_reverse, get_user_auth
from api.taxonomies.serializers import TaxonomyField
from api.nodes.serializers import (
    NodeCitationSerializer,
    NodeLicenseSerializer,
    get_license_details
)
from framework.exceptions import PermissionsError
from website.util import permissions
from website.exceptions import NodeStateError
from website.project import signals as project_signals
from website.models import StoredFileNode, PreprintService, PreprintProvider, Node, NodeLicense


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


class PreprintLicenseRelationshipField(RelationshipField):
    def to_internal_value(self, license_id):
        license = NodeLicense.load(license_id)
        if license:
            return {'license_type': license}
        raise exceptions.NotFound('Unable to find specified license.')


class PreprintSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'date_created',
        'date_modified',
        'date_published',
        'provider',
        'is_published',
    ])

    id = IDField(source='_id', read_only=True)
    subjects = JSONAPIListField(child=JSONAPIListField(child=TaxonomyField()), allow_null=True, required=False)
    date_created = DateByVersion(read_only=True)
    date_modified = DateByVersion(read_only=True)
    date_published = DateByVersion(read_only=True)
    doi = ser.CharField(source='article_doi', required=False, allow_null=True)
    is_published = ser.BooleanField(required=False)
    is_preprint_orphan = ser.BooleanField(read_only=True)
    license_record = NodeLicenseSerializer(required=False, source='license')

    citation = RelationshipField(
        related_view='preprints:preprint-citation',
        related_view_kwargs={'preprint_id': '<_id>'}
    )

    node = NodeRelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
        read_only=False
    )

    license = PreprintLicenseRelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<license.node_license._id>'},
        read_only=False
    )

    provider = PreprintProviderRelationshipField(
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False
    )

    primary_file = PrimaryFileRelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<primary_file._id>'},
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
        return absolute_reverse('preprints:preprint-detail', kwargs={'preprint_id': obj._id, 'version': self.context['request'].parser_context['kwargs']['version']})

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)

    def get_doi_url(self, obj):
        return 'https://dx.doi.org/{}'.format(obj.article_doi) if obj.article_doi else None

    def update(self, preprint, validated_data):
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
            self.set_field(preprint.set_primary_file, primary_file, auth)
            save_node = True

        if 'subjects' in validated_data:
            subjects = validated_data.pop('subjects', None)
            self.set_field(preprint.set_subjects, subjects, auth)
            save_preprint = True

        if 'article_doi' in validated_data:
            preprint.node.preprint_article_doi = validated_data['article_doi']
            save_node = True

        published = validated_data.pop('is_published', None)
        if published is not None:
            self.set_field(preprint.set_published, published, auth)
            save_preprint = True
            recently_published = published

        if 'license_type' in validated_data or 'license' in validated_data:
            license_details = get_license_details(preprint, validated_data)
            self.set_field(preprint.set_preprint_license, license_details, auth)
            save_preprint = True

        if save_node:
            try:
                preprint.node.save()
            except ValidationError as e:
                # Raised from invalid DOI
                raise exceptions.ValidationError(detail=e.messages[0])

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
        except PermissionsError as e:
            raise exceptions.PermissionDenied(detail=e.message)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e.message)
        except NodeStateError as e:
            raise exceptions.ValidationError(detail=e.message)


class PreprintCreateSerializer(PreprintSerializer):
    # Overrides PreprintSerializer to make id nullable, adds `create`
    id = IDField(source='_id', required=False, allow_null=True)

    def create(self, validated_data):
        node = validated_data.pop('node', None)
        if not node:
            raise exceptions.NotFound('Unable to find Node with specified id.')
        elif node.is_deleted:
            raise exceptions.ValidationError('Cannot create a preprint from a deleted node.')

        auth = get_user_auth(self.context['request'])
        if not node.has_permission(auth.user, permissions.ADMIN):
            raise exceptions.PermissionDenied

        primary_file = validated_data.pop('primary_file', None)
        if not primary_file:
            raise exceptions.ValidationError(detail='You must specify a valid primary_file to create a preprint.')

        provider = validated_data.pop('provider', None)
        if not provider:
            raise exceptions.ValidationError(detail='You must specify a valid provider to create a preprint.')

        if PreprintService.find(Q('node', 'eq', node) & Q('provider', 'eq', provider)).count():
            conflict = PreprintService.find_one(Q('node', 'eq', node) & Q('provider', 'eq', provider))
            raise Conflict('Only one preprint per provider can be submitted for a node. Check `meta[existing_resource_id]`.', meta={'existing_resource_id': conflict._id})

        preprint = PreprintService(node=node, provider=provider)
        self.set_field(preprint.set_primary_file, primary_file, auth, save=True)
        preprint.node._has_abandoned_preprint = True
        preprint.node.save()

        return self.update(preprint, validated_data)


class PreprintCitationSerializer(NodeCitationSerializer):

    class Meta:
        type_ = 'preprint-citation'
