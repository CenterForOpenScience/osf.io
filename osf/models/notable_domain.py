from enum import IntEnum

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import LowercaseCharField


class NotableDomain(BaseModel):
    class Note(IntEnum):
        EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT = 0
        ASSUME_HAM_UNTIL_REPORTED = 1
        UNKNOWN = 2
        IGNORED = 3

        @classmethod
        def choices(cls):
            return [
                (int(enum_item), enum_item.name)
                for enum_item in cls
            ]

    domain = LowercaseCharField(max_length=255, unique=True, db_index=True)

    note = models.IntegerField(
        choices=Note.choices(),
        default=Note.UNKNOWN,
    )

    def save(self, *args, **kwargs):
        # Override this method to mark related content
        # as spam or ham when reclassifying domain name
        return super().save(*args, **kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.domain} ({self.Note(self.note).name})>'

    def __str__(self):
        return repr(self)
