from modularodm import Q
from modularodm.exceptions import ValidationValueError, NoResultsFound, MultipleResultsFound
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, IDField, JSONAPIListField, LinksField,
    RelationshipField, TypeField
)
from api.base.exceptions import Conflict
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import NodeTagField
from framework.exceptions import PermissionsError
from website.models import StoredFileNode, PreprintProvider, Node


class PrimaryFileRelationshipField(RelationshipField):
    def get_object(self, file_id):
        return StoredFileNode.load(file_id)

    def to_internal_value(self, data):
        file = self.get_object(data)
        return {'primary_file': file}


class PreprintSubjectField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj._id
        return None

    def to_internal_value(self, data):
        return data

class PreprintSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'id',
        'title',
        'tags',
        'date_created',
        'date_modified',
        'contributors',
        'provider',
        'subjects',
        'doi'
    ])

    title = ser.CharField(required=False)
    subjects = JSONAPIListField(child=PreprintSubjectField(), required=False, source='preprint_subjects')
    provider = ser.CharField(source='preprint_provider', required=False)
    date_created = ser.DateTimeField(read_only=True, source='preprint_created')
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)
    doi = ser.CharField(source='preprint_doi', required=False)

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

    provider = RelationshipField(
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<preprint_provider._id>'},
        lookup_url_kwarg='provider_id'
    )

    links = LinksField(
        {
            'self': 'get_preprint_url',
            'html': 'get_absolute_html_url',
            'doi': 'get_doi_url'
        }
    )

    contributors = RelationshipField(
        related_view='preprints:preprint-contributors',
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
        return 'https://dx.doi.org/{}'.format(obj.preprint_doi)

    def create(self, validated_data):
        node = Node.load(validated_data.pop('_id', None))

        if not node:
            raise exceptions.NotFound('Unable to find Node with specified id.')
        if node.is_preprint:
            raise Conflict('This node already stored as a preprint, use the update method instead.')

        auth = get_user_auth(self.context['request'])
        primary_file = validated_data.pop('primary_file', None)
        if not primary_file:
            raise exceptions.ValidationError(detail='You must specify a primary_file to create a preprint.')

        self.set_node_field(node.set_preprint_file, primary_file, auth)

        subjects = validated_data.pop('preprint_subjects', None)
        if not subjects:
            raise exceptions.ValidationError(detail='You must specify at least one subject to create a preprint.')

        self.set_node_field(node.set_preprint_subjects, subjects, auth)

        for key, value in validated_data.iteritems():
            setattr(node, key, value)
        try:
            node.save()
        except ValidationValueError as e:
            raise exceptions.ValidationError(detail=e.message)
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


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)
    subjects = JSONAPIListField(required=False, source='preprint_subjects')

class PreprintDetailRetrieveSerializer(PreprintDetailSerializer):
    subjects = JSONAPIListField(required=False, source='get_preprint_subjects')


class PreprintPreprintProviderRelationshipSerializer(ser.Serializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    type = TypeField(required=False, allow_null=True)

    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return obj['self'].absolute_api_v2_url + 'relationships/preprints/'

    def get_related_url(self, obj):
        return obj['self'].absolute_api_v2_url + '/preprints/'

    class Meta:
        type_ = 'preprint_providers'

    def make_instance_obj(self, obj):
        return {
            'data': obj.preprint_provider,
            'self': obj
        }

    def update(self, instance, validated_data):
        node = instance['self']
        auth = get_user_auth(self.context['request'])

        if node.preprint_provider:
            raise ValueError('Preprint provider is already assigned to this preprint')

        preprint_provider = PreprintProvider.load(validated_data['_id'])
        node.set_preprint_provider(preprint_provider, auth, save=True)

        return self.make_instance_obj(node)
