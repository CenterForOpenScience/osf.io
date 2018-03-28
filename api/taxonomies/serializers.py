from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, ShowIfVersion
from osf.models import Subject

class TaxonomyField(ser.Field):
    def to_representation(self, subject):
        if not isinstance(subject, Subject):
            subject = Subject.load(subject)
        if subject is not None:
            return {'id': subject._id,
                    'text': subject.text}
        return None

    def to_internal_value(self, subject_id):
        return subject_id


class TaxonomizableSerializerMixin(ser.Serializer):
    """ Mixin for Taxonomizable objects

    Note: subclasses will need to update `filterable_fields` and `update`
    to handle subjects correctly.
    """
    writeable_method_fields = frozenset([
        'subjects'
    ])

    subjects = ser.SerializerMethodField()

    def get_subjects(self, obj):
        from api.taxonomies.serializers import TaxonomyField
        return [
            [
                TaxonomyField().to_representation(subj) for subj in hier
            ] for hier in obj.subject_hierarchy
        ]


class TaxonomySerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'text',
        'parents',
        'parent',
        'id'
    ])
    id = ser.CharField(source='_id', required=True)
    text = ser.CharField(max_length=200)
    parents = ShowIfVersion(
        ser.SerializerMethodField(),
        min_version='2.0',
        max_version='2.3',
    )
    parent = TaxonomyField()
    child_count = ser.SerializerMethodField()
    share_title = ser.CharField(source='provider.share_title', read_only=True)
    path = ser.CharField(read_only=True)

    links = LinksField({
        'parents': 'get_parent_urls',
        'self': 'get_absolute_url',
    })

    def get_child_count(self, obj):
        children_count = getattr(obj, 'children_count', None)
        return children_count if children_count is not None else obj.child_count

    def get_parents(self, obj):
        if not obj.parent:
            return []
        return [TaxonomyField().to_representation(obj.parent)]

    def get_parent_urls(self, obj):
        if obj.parent:
            return [obj.parent.get_absolute_url()]
        return []

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'taxonomies'
