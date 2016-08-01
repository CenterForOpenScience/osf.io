from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer, RelationshipField, IDField, JSONAPIListField, LinksField, Link
)
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
        'primary_file'
    ])

    title = ser.CharField(required=True)
    subjects = ser.CharField(source='preprint_subjects')
    date_created = ser.DateTimeField(read_only=True)
    preprint_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    id = IDField(source='_id', required=False)
    abstract = ser.CharField(source='description', required=False)
    tags = JSONAPIListField(child=NodeTagField(), required=False)

    primary_file = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
    })

    links = LinksField({'html': 'get_absolute_html_url'})

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


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)
