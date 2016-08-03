from rest_framework import serializers as ser
from modularodm import Q

from api.base.serializers import (
    JSONAPISerializer, IDField, JSONAPIListField, LinksField, RelationshipField
)
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import NodeTagField, NodeContributorsSerializer
from website.models import StoredFileNode


class PrimaryFileRelationshipField(RelationshipField):
    def get_object(self, file_id):
        return StoredFileNode.find_one(Q('_id', 'eq', file_id))

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
        'authors',
        'preprint_subjects'
    ])

    title = ser.CharField(required=False)
    subjects = JSONAPIListField(required=False, source='preprint_subjects')
    date_created = ser.DateTimeField(read_only=True, source='preprint_created')
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)

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

    links = LinksField({'self': 'get_preprint_url', 'html': 'get_absolute_html_url'})

    authors = RelationshipField(
        related_view='preprints:preprint-authors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'},
    )

    class Meta:
        type_ = 'preprints'

    def get_preprint_url(self, obj):
        return absolute_reverse('preprints:preprint-detail', kwargs={'node_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)

    def create(self, validated_data):
        node = validated_data.pop('node')
        auth = get_user_auth(self.context['request'])
        node.set_preprint_file(validated_data.pop('primary_file')._id, auth)
        if node._id != validated_data.pop('_id'):
            raise TypeError
        for key, value in validated_data.iteritems():
            setattr(node, key, value)
        node.save()
        return node


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)


class PreprintAuthorSerializer(NodeContributorsSerializer):
    class Meta:
        type_ = 'authors'