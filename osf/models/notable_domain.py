from enum import IntEnum

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from .base import BaseModel
from osf.utils.fields import LowercaseCharField
from osf.external.spam.tasks import reclassify_domain_references


class NotableDomain(BaseModel):
    class Note(IntEnum):
        EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT = 0
        ASSUME_HAM_UNTIL_REPORTED = 1
        UNKNOWN = 2
        IGNORED = 3
        UNVERIFIED = 4  # Timedout couldn't determine

        @classmethod
        def choices(cls):
            return [(int(enum_item), enum_item.name) for enum_item in cls]

    domain = LowercaseCharField(max_length=255, unique=True, db_index=True)

    note = models.IntegerField(
        choices=Note.choices(),
        default=Note.UNKNOWN,
    )

    def save(self, *args, **kwargs):
        db_instance = NotableDomain.load(self.pk)
        super().save(*args, **kwargs)
        if db_instance and self.note != db_instance.note:
            reclassify_domain_references.apply_async(
                kwargs={
                    "notable_domain_id": self.pk,
                    "current_note": self.note,
                    "previous_note": db_instance.note,
                }
            )

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.domain} ({self.Note(self.note).name})>"

    def __str__(self):
        return repr(self)


class DomainReference(BaseModel):
    class Meta:
        unique_together = ("referrer_object_id", "domain")

    referrer_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )
    referrer_object_id = models.PositiveIntegerField()
    referrer = GenericForeignKey("referrer_content_type", "referrer_object_id")
    domain = models.ForeignKey(NotableDomain, on_delete=models.CASCADE)
    is_triaged = models.BooleanField(default=False)
