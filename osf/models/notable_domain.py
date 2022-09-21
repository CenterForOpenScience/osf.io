import re
from enum import IntEnum
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from osf.models.base import BaseModel
from osf.utils.fields import LowercaseCharField

from website import settings


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

    @staticmethod
    def has_spam_domain(content):
        domains = re.findall(
            settings.DOMAIN_REGEX,
            content
        )
        return NotableDomain.objects.filter(
            domain__in=domains,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ).exists()


class DomainReference(BaseModel):
    referrer_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    referrer_object_id = models.PositiveIntegerField()
    referrer = GenericForeignKey('referrer_content_type', 'referrer_object_id')
    domain = models.ForeignKey(NotableDomain, on_delete=models.CASCADE)
    is_triaged = models.BooleanField(default=False)
