from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField


class SubjectSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'text',
        'parent',
        'id',
    ])
    id = ser.CharField(source='_id', required=True)
    text = ser.CharField(max_length=200)

    parent = RelationshipField(
        related_view='subjects:subject-detail',
        related_view_kwargs={'subject_id': '<parent._id>'},
    )

    children = RelationshipField(
        related_view='subjects:subject-children',
        related_view_kwargs={'subject_id': '<_id>'},
        related_meta={'count': 'get_children_count'},

    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_subject_url

    def get_children_count(self, obj):
        return obj.child_count()

    class Meta:
        type_ = 'subjects'
