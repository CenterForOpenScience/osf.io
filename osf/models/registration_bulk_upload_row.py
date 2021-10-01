import hashlib
from django.db import models

from osf.models.base import BaseModel
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import ensure_bytes


class RegistrationBulkUploadRow(BaseModel):
    """Defines a database table that stores information about to-be-created (draft) registrations.
    """

    # The bulk upload to which this registration belongs
    upload = models.ForeignKey('RegistrationBulkUploadJob', blank=False, null=True, on_delete=models.CASCADE)

    # The draft registration that have been successfully created
    draft_registration = models.ForeignKey('DraftRegistration', blank=True, null=True, on_delete=models.CASCADE)

    # A flag that indicates whether the draft registration has been created
    is_completed = models.BooleanField(default=False)

    # A flag that indicates whether the draft registration creation is in progress
    is_picked_up = models.BooleanField(default=False)

    # The raw text string of a row in the CSV template
    csv_raw = models.TextField(default='', blank=False, null=False)

    # The parsed version of the above raw text string.
    # TODO: add a comment here for the expected format of the value
    csv_parsed = DateTimeAwareJSONField(default=dict, blank=False, null=False)

    row_hash = models.CharField(default='', blank=False, null=False, unique=True, max_length=255)

    @classmethod
    def create(cls, upload, csv_raw, csv_parsed):
        registration_row = cls(upload=upload, draft_registration=None, is_completed=False,
                               is_picked_up=False, csv_raw=csv_raw, csv_parsed=csv_parsed,
                               row_hash=hashlib.md5(ensure_bytes(csv_raw)).hexdigest(),)
        return registration_row
