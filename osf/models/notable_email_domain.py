from enum import Enum

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import LowercaseCharField


def enum_choices(enum_cls):
    return [
        (enum_item.value, enum_item.name)
        for enum_item in enum_cls
    ]

class NotableEmailDomain(BaseModel):
    class Note(Enum):
        EXCLUDE_FROM_ACCOUNT_CREATION = 0
        ASSUME_HAM_UNTIL_REPORTED = 1

    domain = LowercaseCharField(max_length=255, unique=True, db_index=True)

    note = models.IntegerField(
        choices=enum_choices(Note),
        default=Note.EXCLUDE_FROM_ACCOUNT_CREATION.value,
    )

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.domain} ({self.Note(self.note).name})>'

    def __str__(self):
        return repr(self)
