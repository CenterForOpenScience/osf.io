from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer, RelationshipField, IDField, JSONAPIListField, LinksField
)
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

    title = ser.CharField(required=True)
    preprint_subjects = JSONAPIListField()
    date_created = ser.DateTimeField(read_only=True, source='preprint_created')
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)

    primary_file = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<_id>'},
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


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)


class PreprintAuthorSerializer(NodeContributorsSerializer):
    class Meta:
        type_ = 'authors'