from rest_framework import serializers as ser

from addons.osfstorage.models import OsfStorageFile
from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from api.files.serializers import get_file_download_link
from api.nodes.serializers import NodeSerializer


class MeetingSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
        'location',
    ])

    id = IDField(source='endpoint', read_only=True)
    type = TypeField()
    name = ser.CharField(read_only=True)
    location = ser.CharField(read_only=True)
    start_date = VersionedDateTimeField(read_only=True)
    end_date = VersionedDateTimeField(read_only=True)
    info_url = ser.URLField(read_only=True)
    logo_url = ser.URLField(read_only=True)
    field_names = ser.DictField(read_only=True)
    submissions_count = ser.SerializerMethodField()
    active = ser.BooleanField(read_only=True)
    type_one_submission_email = ser.SerializerMethodField()
    type_two_submission_email = ser.SerializerMethodField()
    is_accepting_type_one = ser.BooleanField(source='poster', read_only=True)
    is_accepting_type_two = ser.BooleanField(source='talk', read_only=True)

    submissions = RelationshipField(
        related_view='meetings:meeting-submissions',
        related_view_kwargs={'meeting_id': '<endpoint>'},
        related_meta={'count': 'get_submissions_count'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'html': 'get_absolute_html_url',
    })

    def format_submission_email(self, obj, submission_field):
        if obj.active:
            return '{}-{}@osf.io'.format(obj.endpoint, obj.field_names.get(submission_field))
        return ''

    def get_type_one_submission_email(self, obj):
        return self.format_submission_email(obj, 'submission1')

    def get_type_two_submission_email(self, obj):
        return self.format_submission_email(obj, 'submission2')

    def get_absolute_url(self, obj):
        return absolute_reverse('meetings:meeting-detail', kwargs={'meeting_id': obj.endpoint})

    def get_submissions_count(self, obj):
        if getattr(obj, 'submissions_count', None):
            return obj.submissions_count
        else:
            return obj.valid_submissions.count()

    class Meta:
        type_ = 'meetings'


class MeetingSubmissionSerializer(NodeSerializer):
    filterable_fields = frozenset([
        'title',
        'meeting_category',
        'author_name',
    ])

    author_name = ser.SerializerMethodField()
    download_count = ser.SerializerMethodField()
    meeting_category = ser.SerializerMethodField()

    author = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': 'get_author_id'},
        read_only=True,
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'html': 'get_absolute_html_url',
        'download': 'get_download_link',
    })

    def get_author(self, obj):
        contrib_queryset = obj.contributor_set.filter(visible=True).order_by('_order')
        if contrib_queryset:
            return contrib_queryset.first().user
        return None

    def get_author_id(self, obj):
        # Author guid is annotated on queryset in ListView
        if getattr(obj, 'author_id', None):
            return obj.author_id
        else:
            author = self.get_author(obj)
            return author._id if author else None

    def get_author_name(self, obj):
        """
        Returns the first bibliographic contributor's family_name if it exists.
        Otherwise, return its fullname.
        """
        if getattr(obj, 'author_name', None):
            # Field is annotated on queryset in ListView for filtering purposes
            return obj.author_name
        else:
            author = self.get_author(obj)
            if author:
                return author.family_name if author.family_name else author.fullname
            return None

    def get_meeting_category(self, obj):
        """
        Returns the existance of a certain tag on the node.  If the first submission type tag exists,
        return that.  Otherwise, return the second submission type tag as a default.
        """
        if getattr(obj, 'meeting_category', None):
            # Field is annotated on queryset in ListView for filtering purposes
            return obj.meeting_category
        else:
            meeting = self.context['meeting']
            submission1_name = meeting.field_names.get('submission1')
            submission2_name = meeting.field_names.get('submission2')
            submission_tags = obj.tags.values_list('name', flat=True)
            return submission1_name if submission1_name in submission_tags else submission2_name

    def get_download_count(self, obj):
        """
        Return the download counts of the first osfstorage file
        """
        if getattr(obj, 'download_count', None):
            return obj.download_count or 0
        else:
            submission_file = self.get_submission_file(obj)
            return submission_file.get_download_count() if submission_file else None

    def get_download_link(self, obj):
        """
        First osfstoragefile on a node - if the node was created for a meeting,
        assuming its first file is the meeting submission.
        """
        if getattr(obj, 'file_id', None):
            submission_file = OsfStorageFile.objects.get(id=obj.file_id)
        else:
            submission_file = self.get_submission_file(obj)

        if submission_file:
            return get_file_download_link(submission_file)
        return None

    def get_submission_file(self, obj):
        return obj.files.order_by('created').first()

    def get_absolute_url(self, obj):
        meeting_endpoint = self.context['meeting'].endpoint
        return absolute_reverse(
            'meetings:meeting-submission-detail',
            kwargs={
                'meeting_id': meeting_endpoint,
                'submission_id': obj._id,
            },
        )

    # Overrides SparseFieldsetMixin
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        """
        Since meeting submissions are actually nodes, we are subclassing the NodeSerializer,
        but we only want to return a subset of fields specific to meetings
        """
        fieldset = [
            'date_created',
            'title',
            'author',
            'author_name',
            'meeting_category',
            'download_count',
            'submission_file',
        ]
        for field_name in self.fields.fields.copy().keys():
            if field_name in ('id', 'links', 'type'):
                # MUST return these fields
                continue
            if field_name not in fieldset:
                self.fields.pop(field_name)
        return super(MeetingSubmissionSerializer, self).parse_sparse_fields(allow_unsafe, **kwargs)

    class Meta:
        type_ = 'meeting-submissions'
