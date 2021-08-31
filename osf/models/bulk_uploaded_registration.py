import logging

from django.db import models

from osf.models.base import BaseModel
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

logger = logging.getLogger(__name__)


class BulkUploadedRegistration(BaseModel):
    """Defines a database table of which each row stores information about one to-be-created registration.
    """

    # The id that registration provider uses to identify each to-be-created registration in one upload
    external_id = models.CharField(blank=False, null=False, max_length=255)

    # The bulk upload to which this registration belongs
    upload = models.ForeignKey('RegistrationBulkUpload', blank=False, null=True, on_delete=models.CASCADE)

    # The draft registration that have been successfully created
    draft_registration = models.ForeignKey('DraftRegistration', null=True, blank=True, on_delete=models.CASCADE)

    # A flag that indicates whether the draft registration has been created
    is_completed = models.BooleanField(default=False)

    # A flag that indicates whether the draft registration creation is in progress
    is_picked_up = models.BooleanField(default=False)

    # The raw text string of a row in the CSV template
    csv_raw = models.TextField(default='', blank=False, null=False, unique=True)

    # The parsed version of the above raw text string.
    # TODO: add/update comments here for the expected format of the value
    csv_parsed = DateTimeAwareJSONField(default=dict, blank=False, null=False)

    @classmethod
    def create(cls, external_id, upload, csv_raw, csv_parsed):
        registration_row = cls(external_id=external_id, upload=upload, draft_registration=None,
                               is_completed=False, is_picked_up=False, csv_raw=csv_raw, csv_parsed=csv_parsed)
        return registration_row
