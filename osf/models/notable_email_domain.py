from enum import IntEnum

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import LowercaseCharField


class NotableEmailDomain(BaseModel):
    class Note(IntEnum):
        EXCLUDE_FROM_ACCOUNT_CREATION = 0
        ASSUME_HAM_UNTIL_REPORTED = 1

        @classmethod
        def choices(cls):
            return [
                (int(enum_item), enum_item.name)
                for enum_item in cls
            ]

    domain = LowercaseCharField(max_length=255, unique=True, db_index=True)

    note = models.IntegerField(
        choices=Note.choices(),
        default=Note.EXCLUDE_FROM_ACCOUNT_CREATION,
    )

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.domain} ({self.Note(self.note).name})>'

    def __str__(self):
        return repr(self)
