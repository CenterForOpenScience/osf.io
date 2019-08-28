from rest_framework import serializers as ser

from distutils.version import StrictVersion

from api.base.serializers import JSONAPISerializer, LinksField, ShowIfVersion, RelationshipField
from api.subjects.serializers import UpdateSubjectsMixin
from osf.models import Subject

subjects_as_relationships_version = '2.16'

class TaxonomyField(ser.Field):
    def to_representation(self, subject):
        if not isinstance(subject, Subject):
            subject = Subject.load(subject)
        if subject is not None:
            return {
                'id': subject._id,
                'text': subject.text,
            }
        return None

    def to_internal_value(self, subject_id):
        return subject_id


class TaxonomizableSerializerMixin(ser.Serializer, UpdateSubjectsMixin):
    """ Mixin for Taxonomizable objects

    Note: subclasses will need to update `filterable_fields` and `update`
    to handle subjects correctly.
    """
    writeable_method_fields = frozenset([
        'subjects',
    ])

    def __init__(self, *args, **kwargs):
        super(TaxonomizableSerializerMixin, self).__init__(*args, **kwargs)
        request = kwargs['context']['request']

        if self.expect_subjects_as_relationships(request):
            subject_kwargs = {
                'related_view': self.subjects_related_view,
                'related_view_kwargs': self.subjects_view_kwargs,
                'read_only': False,
                'many': True,
                'required': False,
            }

            if self.subjects_self_view:
                subject_kwargs['self_view'] = self.subjects_self_view
                subject_kwargs['self_view_kwargs'] = self.subjects_view_kwargs

            self.fields['subjects'] = RelationshipField(**subject_kwargs)
        else:
            self.fields['subjects'] = ser.SerializerMethodField()

    @property
    def subjects_related_view(self):
        """
        For dynamically building the subjects RelationshipField on __init__

        Return format '<view_category>:<view_name>, for the desired related view,
        for example, 'nodes:node-subjects'
        """
        raise NotImplementedError()

    @property
    def subjects_view_kwargs(self):
        """
        For dynamically building the subjects RelationshipField on __init__

        Return kwargs needed to build the related/self view links,
        for example: {'node_id': '<_id>'}
        """
        raise NotImplementedError

    @property
    def subjects_self_view(self):
        """
        Optional: For dynamically building the subjects RelationshipField on __init__

        If you're going to provide a subjects `self` link, return the desired self view
        in format '<view_category>:<view_name>.

        For example, 'nodes:node-relationships-subjects'
        """
        pass

    def get_subjects(self, obj):
        """
        `subjects` is a SerializerMethodField for older versions of the API,
        serialized under attributes
        """
        from api.taxonomies.serializers import TaxonomyField
        return [
            [
                TaxonomyField().to_representation(subj) for subj in hier
            ] for hier in obj.subject_hierarchy
        ]

    # Overrides UpdateSubjectsMixin
    def update_subjects_method(self, resource, subjects, auth):
        """Depending on the request's version, runs a different method
        to update the resource's subjects. Will expect request to be formatted
        differently, depending on the version.

        :param object resource: Object for which you want to update subjects
        :param list subjects: Subjects array (or array of arrays)
        :param object Auth object
        """
        if self.expect_subjects_as_relationships(self.context['request']):
            return resource.set_subjects_from_relationships(subjects, auth)
        return resource.set_subjects(subjects, auth)

    def expect_subjects_as_relationships(self, request):
        """Determines whether subjects should be serialized as a relationship.
        Earlier versions serialize subjects as an attribute(before 2.16).
        Version 2.16 and later serializer subjects as relationships.

        :param object request: Request object
        :return bool: Subjects should be serialized as relationships
        """
        return StrictVersion(getattr(request, 'version', '2.0')) >= StrictVersion(subjects_as_relationships_version)


class TaxonomySerializer(JSONAPISerializer):
    """
    Will be deprecated in the future and replaced by SubjectSerializer
    """
    filterable_fields = frozenset([
        'text',
        'parents',
        'parent',
        'id',
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
