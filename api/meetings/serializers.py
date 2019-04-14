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

    submissions = RelationshipField(
        related_view='meetings:meeting-submissions',
        related_view_kwargs={'meeting_id': '<endpoint>'},
        related_meta={'count': 'get_submissions_count'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'html': 'get_absolute_html_url',
    })

    def get_submissions_count(self, obj):
        return obj.submissions.count()

    def get_absolute_url(self, obj):
        return absolute_reverse('meetings:meeting-detail', kwargs={'meeting_id': obj.endpoint})

    class Meta:
        type_ = 'meetings'


class MeetingSubmissionSerializer(NodeSerializer):

    meeting_submission = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': 'get_meeting_submission_id'},
        read_only=False,
        related_meta={'download_count': 'get_submission_download_count'},
    )

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
