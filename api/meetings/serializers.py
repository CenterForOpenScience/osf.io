from rest_framework import serializers as ser

from django.contrib.contenttypes.models import ContentType
from django.db import connection

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from osf.models import AbstractNode


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
    # num_submissions is cached in the view
    submissions_count = ser.IntegerField(source='num_submissions', read_only=True)
    active = ser.BooleanField(read_only=True)
    submission_1_email = ser.SerializerMethodField()
    submission_2_email = ser.SerializerMethodField()

    submissions = RelationshipField(
        related_view='meetings:meeting-submissions',
        related_view_kwargs={'meeting_id': '<endpoint>'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'html': 'get_absolute_html_url',
    })

    def format_submission_email(self, obj, submission_field):
        if obj.active:
            return '{}-{}@osf.io'.format(obj.endpoint, obj.field_names.get(submission_field))
        return ''

    def get_submission_1_email(self, obj):
        return self.format_submission_email(obj, 'submission1')

    def get_submission_2_email(self, obj):
        return self.format_submission_email(obj, 'submission2')

    def get_absolute_url(self, obj):
        return absolute_reverse('meetings:meeting-detail', kwargs={'meeting_id': obj.endpoint})

    class Meta:
        type_ = 'meetings'


class MeetingSubmissionSerializer(NodeSerializer):
    filterable_fields = frozenset([
        'title',
        'tags',
        'date_created',
        'author_name',
    ])

    author_name = ser.SerializerMethodField()

    author = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': 'get_author_id'},
        read_only=True,
    )

    meeting_submission = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': 'get_meeting_submission_id'},
        read_only=True,
        related_meta={'download_count': 'get_submission_download_count'},
    )

    def get_author(self, obj):
        contrib_queryset = obj.contributor_set.filter(visible=True).order_by('_order')
        if contrib_queryset:
            return contrib_queryset.first().user
        return None

    def get_author_id(self, obj):
        author = self.get_author(obj)
        return author._id if author else None

    def get_author_name(self, obj):
        author = self.get_author(obj)
        if author:
            return author.family_name if author.family_name else author.fullname
        return None

    def get_submission_download_count(self, obj):
        """
        Return the download counts of the first osfstorage file
        """
        node_ct = ContentType.objects.get_for_model(AbstractNode).id
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT P.total
                FROM osf_basefilenode F, osf_pagecounter P
                WHERE (F.type = 'osf.osfstoragefile'
                     AND F.provider = 'osfstorage'
                     AND F.target_content_type_id = %s
                     AND F.target_object_id = %s
                     AND P._id = 'download:' || %s || ':' || F._id)
                ORDER BY F.id ASC
                LIMIT 1;
            """, [node_ct, obj.id, obj._id],
            )
            result = cursor.fetchone()
            if result:
                return int(result[0])
            return 0

    def get_meeting_submission_id(self, obj):
        """
        First osfstoragefile on a node - if the node was created for a meeting,
        assuming its first file is the meeting submission.
        """
        first_file = obj.files.first()
        return first_file._id if first_file else None
