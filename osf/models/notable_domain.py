from enum import IntEnum

from django.db import models

from osf.models.base import BaseModel


class NotableDomain(BaseModel):
    class Note(IntEnum):
        SPAM = 0
        HAM = 1
        UNKNOWN = 2

        @classmethod
        def choices(cls):
            return [
                (int(enum_item), enum_item.name)
                for enum_item in cls
            ]

    domain = models.URLField(max_length=255, unique=True, db_index=True)

    note = models.IntegerField(
        choices=Note.choices(),
        default=Note.SPAM,
    )

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.domain} ({self.Note(self.note).name})>'

    def __str__(self):
        return repr(self)
