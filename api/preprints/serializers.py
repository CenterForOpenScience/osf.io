from rest_framework import serializers as ser
from modularodm import Q
from modularodm.exceptions import NoResultsFound, MultipleResultsFound
from api.base.serializers import (
    JSONAPISerializer, RelationshipField, IDField, JSONAPIListField, LinksField
)
from website.models import Node
from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeTagField, NodeContributorsSerializer


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

    primary_file = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<preprint_file._id>'},
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
        node = validated_data.get('node')
        # TODO - get correct fields from validated_data
        pass


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)


class PreprintAuthorSerializer(NodeContributorsSerializer):
    class Meta:
        type_ = 'authors'