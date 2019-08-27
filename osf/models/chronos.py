from __future__ import unicode_literals
from django.db import models
from osf.models.base import BaseModel
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.workflows import ChronosSubmissionStatus


class ChronosJournal(BaseModel):
    name = models.TextField(null=False, blank=False)
    title = models.TextField(null=False, blank=False)
    journal_id = models.TextField(unique=True, null=False, blank=False)

    raw_response = DateTimeAwareJSONField(null=False, blank=False)

    primary_identifier_name = 'journal_id'

    def __repr__(self):
        return '<{}({} - {})>'.format(
            self.__class__.__name__,
            self.name,
            self.title,
        )


class ChronosSubmission(BaseModel):
    publication_id = models.TextField(null=False, blank=False, unique=True)

    journal = models.ForeignKey(ChronosJournal, null=False, blank=False)
    preprint = models.ForeignKey('osf.Preprint', null=False, blank=False)

    submitter = models.ForeignKey('osf.OSFUser', null=False, blank=False)

    status = models.IntegerField(null=True, blank=True, default=None, choices=ChronosSubmissionStatus.choices())

    raw_response = DateTimeAwareJSONField(null=False, blank=False)
    submission_url = models.TextField(null=False, blank=False)

    class Meta:
        unique_together = [
            ('preprint', 'journal')
        ]

    def __repr__(self):
        return '<{}(journal={!r}, preprint={!r}, submitter={!r}, status={!r})>'.format(
            self.__class__.__name__,
            self.journal,
            self.preprint,
            self.submitter,
            self.status,
        )
