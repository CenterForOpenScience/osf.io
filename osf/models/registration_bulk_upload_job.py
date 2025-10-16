from enum import IntEnum

from django.db import models

from .base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField


class JobState(IntEnum):
    """Defines the six states of registration bulk upload jobs.
    """

    PENDING = 0  # Database preparation is in progress
    INITIALIZED = 1  # Database preparation has been finished and is ready to be picked up
    PICKED_UP = 2  # Registration creation is in progress
    DONE_FULL = 3  # All (draft) registrations have been successfully created
    DONE_PARTIAL = 4  # Some (draft) registrations have failed the creation process
    DONE_ERROR = 5  # All (draft) registrations have failed


class RegistrationBulkUploadJob(BaseModel):
    """Defines a database table that stores registration bulk upload jobs.
    """

    # The hash of the CSV template payload
    payload_hash = models.CharField(blank=False, null=False, unique=True, max_length=255)

    # The status/state of the bulk upload
    state = models.IntegerField(choices=[(state, state.name) for state in JobState], default=JobState.PENDING)

    # The user / admin who started this bulk upload
    initiator = models.ForeignKey('OSFUser', blank=False, null=True, on_delete=models.CASCADE)

    # The registration provider this bulk upload targets
    provider = models.ForeignKey('RegistrationProvider', blank=False, null=True, on_delete=models.CASCADE)

    # The registration template this bulk upload uses
    schema = models.ForeignKey('RegistrationSchema', blank=False, null=True, on_delete=models.CASCADE)

    # The date when success / failure emails are sent after the creation of registrations in this upload has been done
    email_sent = NonNaiveDateTimeField(blank=True, null=True)

    @classmethod
    def create(cls, payload_hash, initiator, provider, schema, state=JobState.PENDING, email_sent=None):
        upload = cls(
            payload_hash=payload_hash,
            state=state,
            initiator=initiator,
            provider=provider,
            schema=schema,
            email_sent=email_sent,
        )
        return upload
