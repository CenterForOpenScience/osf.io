from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer, RelationshipField, IDField, JSONAPIListField, LinksField, Link
)
from api.nodes.serializers import NodeTagField

class PreprintSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'title',
        'subjects',
        'date_created',
        'authors',
        'abstract',
        'id',
        'tags',
        'primary_file',
    ])
    title = ser.CharField(required=True)
    subjects = ser.CharField(source='preprint_subjects')
    date_created = ser.DateTimeField(read_only=True, source='preprint_created')
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

    root = RelationshipField(
        related_view='preprints:preprint-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    )
    class Meta:
        type_ = 'preprints'


class PreprintDetailSerializer(PreprintSerializer):
    id = IDField(source='_id', required=True)
