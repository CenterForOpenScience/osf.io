import re
import operator
from enum import IntEnum
from functools import reduce
from urllib.parse import urlparse
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
    def check_resource_for_domains(obj, confirm_spam=False, send_to_moderation=False):
        fields_to_query = []
        for field in list(obj.SPAM_CHECK_FIELDS):
            fields_to_query += [models.Q(**{f'{field}__regex': settings.DOMAIN_REGEX})]
        query = reduce(operator.or_, fields_to_query)
        has_domain = obj.__class__.objects.filter(query).filter(id=obj.id).exists()

        if not has_domain:
            return False
        elif confirm_spam and NotableDomain.has_spam_domain(obj):
            obj.confirm_spam(save=True)
        elif send_to_moderation:
            NotableDomain.add_domains_to_moderation_queue(obj)
        obj.save()
        return True

    @staticmethod
    def add_domains_to_moderation_queue(obj):
        fields_to_query = []
        spam_fields = list(obj.SPAM_CHECK_FIELDS)
        for field in spam_fields:
            fields_to_query += [models.Q(**{f'{field}__regex': settings.DOMAIN_REGEX})]
        query = reduce(operator.or_, fields_to_query)
        raw_field_content = str(obj.__class__.objects.filter(query).filter(id=obj.id).values(*spam_fields))

        urls = re.findall(settings.DOMAIN_REGEX, raw_field_content)
        for url in urls:
            domain = urlparse(url)
            notable_domain, created = NotableDomain.objects.get_or_create(
                domain=f'{domain.scheme}://{domain.netloc}',  # remove path and query params
                defaults={'note': NotableDomain.Note.UNKNOWN}
            )
            DomainReference.objects.get_or_create(
                domain=notable_domain,
                referrer_object_id=obj.id,
                referrer_content_type=ContentType.objects.get_for_model(obj)
            )

    @staticmethod
    def has_spam_domain(obj):
        spam_fields = list(obj.SPAM_CHECK_FIELDS)
        raw_field_content = str(obj.__class__.objects.filter(id=obj.id).values(*spam_fields))
        domains = re.findall(settings.DOMAIN_REGEX, raw_field_content)
        return NotableDomain.objects.filter(
            domain__in=domains,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        )


class DomainReference(BaseModel):
    referrer_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    referrer_object_id = models.PositiveIntegerField()
    referrer = GenericForeignKey('referrer_content_type', 'referrer_object_id')
    domain = models.ForeignKey(NotableDomain, on_delete=models.CASCADE)
    is_triaged = models.BooleanField(default=False)
