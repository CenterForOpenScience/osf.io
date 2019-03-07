from rest_framework import serializers as ser
from rest_framework.exceptions import NotFound

from api.base.exceptions import Conflict
from api.base.serializers import JSONAPISerializer, RelationshipField, LinksField
from api.base.utils import absolute_reverse
from osf.external.chronos import ChronosClient
from osf.models import ChronosJournal
from osf.utils.workflows import ChronosSubmissionStatus

class ChronosJournalRelationshipField(RelationshipField):
    def to_internal_value(self, journal_id):
        try:
            journal = ChronosJournal.objects.get(journal_id=journal_id)
        except ChronosJournal.DoesNotExist:
            raise NotFound('Unable to find specified journal.')
        return {'journal': journal}

class ChronosJournalSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'chronos-journals'

    filterable_fields = frozenset(['title', 'name', 'id'])

    id = ser.CharField(source='journal_id', read_only=True)
    name = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)

    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return absolute_reverse('chronos:chronos-journal-detail', kwargs={'journal_id': obj.journal_id})


class ChronosSubmissionSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'chronos-submissions'

    id = ser.CharField(source='publication_id', read_only=True)
    submission_url = ser.CharField(read_only=True)
    status = ser.SerializerMethodField()
    modified = ser.DateTimeField(read_only=True)

    journal = RelationshipField(
        read_only=True,
        related_view='chronos:chronos-journal-detail',
        related_view_kwargs={'journal_id': '<journal.journal_id>'},
    )
    preprint = RelationshipField(
        read_only=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<preprint._id>'},
    )
    submitter = RelationshipField(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<submitter._id>'},
    )
    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return absolute_reverse('chronos:chronos-submission-detail', kwargs={'preprint_id': obj.preprint._id, 'submission_id': obj.publication_id})

    def get_status(self, obj):
        value_lookup = {val.value: key for key, val in ChronosSubmissionStatus.__members__.items()}
        return value_lookup[obj.status]


class ChronosSubmissionDetailSerializer(ChronosSubmissionSerializer):
    id = ser.CharField(source='publication_id', required=True)

    def update(self, instance, validated_data):
        return ChronosClient().update_manuscript(instance)


class ChronosSubmissionCreateSerializer(ChronosSubmissionSerializer):
    journal = ChronosJournalRelationshipField(
        read_only=False,
        related_view='chronos:chronos-journal-detail',
        related_view_kwargs={'journal_id': '<journal.journal_id>'},
    )

    def create(self, validated_data):
        journal = validated_data.pop('journal')
        preprint = validated_data.pop('preprint')
        submitter = validated_data.pop('submitter')
        try:
            return ChronosClient().submit_manuscript(journal=journal, preprint=preprint, submitter=submitter)
        except ValueError as e:
            raise Conflict(e.message)
