import hashlib
from django.db import models

from osf.exceptions import RegistrationBulkCreationContributorError
from .base import BaseModel
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import ensure_bytes
from osf.utils.permissions import READ, WRITE, ADMIN


class RegistrationBulkUploadRow(BaseModel):
    """Defines a database table that stores information about to-be-created (draft) registrations."""

    # The bulk upload to which this registration belongs
    upload = models.ForeignKey(
        "RegistrationBulkUploadJob",
        blank=False,
        null=True,
        on_delete=models.CASCADE,
    )

    # The draft registration that have been successfully created
    draft_registration = models.ForeignKey(
        "DraftRegistration", blank=True, null=True, on_delete=models.CASCADE
    )

    # A flag that indicates whether the draft registration has been created
    is_completed = models.BooleanField(default=False)

    # A flag that indicates whether the draft registration creation is in progress
    is_picked_up = models.BooleanField(default=False)

    # The raw text string of a row in the CSV template
    csv_raw = models.TextField(default="", blank=False, null=False)

    # The parsed version of the above raw text string.
    # TODO: add a comment here for the expected format of the value
    csv_parsed = DateTimeAwareJSONField(default=dict, blank=False, null=False)

    row_hash = models.CharField(
        default="", blank=False, null=False, unique=True, max_length=255
    )

    @classmethod
    def create(
        cls,
        upload,
        csv_raw,
        csv_parsed,
        draft_registration=None,
        is_completed=False,
        is_picked_up=False,
    ):
        registration_row = cls(
            upload=upload,
            draft_registration=draft_registration,
            is_completed=is_completed,
            is_picked_up=is_picked_up,
            csv_raw=csv_raw,
            csv_parsed=csv_parsed,
            row_hash=hashlib.md5(ensure_bytes(csv_raw)).hexdigest(),
        )
        return registration_row

    # Overrides Django model's default `__hash__()` method to support pre-save hashing without PK
    def __hash__(self):
        if self._get_pk_val() is None:
            # `self.row_hash` is a MD5 hex-digest string, must call the built-in `hash()` to get an integer
            return hash(self.row_hash)
        return hash(self._get_pk_val())

    # Overrides Django model's default `__eq__()` method to support pre-save equality check without PK
    def __eq__(self, other):
        if not isinstance(other, RegistrationBulkUploadRow):
            return False
        my_pk = self._get_pk_val()
        if my_pk is None:
            return self.row_hash == other.row_hash
        return my_pk == other._get_pk_val()


class RegistrationBulkUploadContributors:
    """A helper class of which an instance contains parsed data about contributors per registration row."""

    def __init__(
        self,
        admin_set,
        read_only_set,
        read_write_set,
        author_set,
        contributor_list,
    ):
        self.contributor_list = contributor_list
        self.admin_set = admin_set
        self.read_write_set = read_write_set
        self.read_only_set = read_only_set
        self.author_set = author_set

    def is_bibliographic(self, email):
        return email in self.author_set

    def get_permission(self, email):
        if email in self.admin_set:
            return ADMIN
        elif email in self.read_write_set:
            return WRITE
        elif email in self.read_only_set:
            return READ
        else:
            raise RegistrationBulkCreationContributorError(
                error=f"{email} does not have a permission"
            )
