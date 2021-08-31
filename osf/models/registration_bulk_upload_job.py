import logging

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField

logger = logging.getLogger(__name__)


class RegistrationBulkUploadJob(BaseModel):
    """Defines a database table that stores registration bulk upload jobs.
    """

    # The hash of the CSV template payload
    payload_hash = models.CharField(blank=False, null=False, unique=True, max_length=255)

    # The status/state of the bulk upload
    state = models.CharField(choices=[
        ('pending', 'Database preparation in progress'),
        ('initialized', 'Database preparation done'),
        ('picked_up', 'Registration creation in progress'),
        ('done_full', 'All (draft) registrations have been created'),
        ('done_partial', 'Some (draft) registrations have failed creation'),
        ('done_error', 'All have failed'),
    ], max_length=255)

    # The user / admin who started this bulk upload
    initiator = models.ForeignKey('OSFUser', null=True, on_delete=models.CASCADE)

    # The registration provider this bulk upload targets
    provider = models.ForeignKey('RegistrationProvider', null=True, on_delete=models.CASCADE)

    # The registration template this bulk upload uses
    schema = models.ForeignKey('RegistrationSchema', blank=False, null=True, on_delete=models.CASCADE)

    # The date when success / failure emails are sent after the creation of registrations in this upload has been done
    email_sent = NonNaiveDateTimeField(null=True, blank=True)

    @classmethod
    def create(cls, payload_hash, initiator, provider, schema):
        upload = cls(payload_hash=payload_hash, state='pending',
                     initiator=initiator, provider=provider, schema=schema, email_sent=None)
        return upload
