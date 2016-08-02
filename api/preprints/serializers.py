from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer, RelationshipField, IDField, JSONAPIListField, LinksField
)
from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeTagField


class PreprintSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'id',
        'title',
        'description',
        'public',
        'tags',
        'date_created',
        'date_modified',
        'preprint_created',
        'root',
        'parent',
        'contributors',
        'preprint_subjects'
    ])

    title = ser.CharField(required=True)
    preprint_subjects = JSONAPIListField()
    date_created = ser.DateTimeField(read_only=True)
    preprint_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)

    primary_file = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<_id>'},
    )

    links = LinksField({'self': 'get_preprint_url', 'html': 'get_absolute_html_url'})

    authors = RelationshipField(
        related_view='preprints:preprint-authors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'},
    )

    parent = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    )

    root = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    )

    class Meta:
        type_ = 'preprints'

    def get_preprint_url(self, obj):
        return absolute_reverse('preprints:preprint-detail', kwargs={'node_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)
