# -*- coding: utf-8 -*-
from django.db import models
from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
SCHEMABLOCK_TYPES = [
    ('page-heading', 'page-heading'),
    ('section-heading', 'section-heading'),
    ('subsection-heading', 'subsection-heading'),
    ('paragraph', 'paragraph'),
    ('question-label', 'question-label'),
    ('short-text-input', 'short-text-input'),
    ('long-text-input', 'long-text-input'),
    ('file-input', 'file-input'),
    ('contributors-input', 'contributors-input'),
    ('single-select-input', 'single-select-input'),
    ('multi-select-input', 'multi-select-input'),
    ('select-input-option', 'select-input-option'),
    ('select-other-option', 'select-other-option'),
]


class AbstractSchemaBlock(ObjectIDMixin, BaseModel):
    class Meta:
        abstract = True
        order_with_respect_to = 'schema'
        unique_together = ('schema', 'response_key')

    INPUT_BLOCK_TYPES = frozenset([
        'short-text-input',
        'long-text-input',
        'file-input',
        'contributors-input',
        'single-select-input',
        'multi-select-input',
        'select-other-option',
    ])

    help_text = models.TextField()
    example_text = models.TextField(null=True)
    # Corresponds to a key in DraftRegistration.registration_responses dictionary
    response_key = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    # A question can be split into multiple schema blocks, but are linked with a schema_block_group_key
    schema_block_group_key = models.CharField(max_length=24, db_index=True, null=True)
    block_type = models.CharField(max_length=31, db_index=True, choices=SCHEMABLOCK_TYPES)
    display_text = models.TextField()
    required = models.BooleanField(default=False)

    @property
    def absolute_api_v2_url(self):
        return api_v2_url(f'{self.schema.absolute_api_v2_url}schema_blocks/{ self._id}/')

    def save(self, *args, **kwargs):
        """
        Allows us to use a unique_together constraint, so each "response_key"
        only appears once for every registration schema.  To do this, we need to save
        empty "response_key"s as null, instead of an empty string.
        """
        self.response_key = self.response_key or None
        return super().save(*args, **kwargs)


class RegistrationSchemaBlock(AbstractSchemaBlock):
    schema = models.ForeignKey('RegistrationSchema', related_name='schema_blocks', on_delete=models.CASCADE)


class FileSchemaBlock(AbstractSchemaBlock):
    schema = models.ForeignKey('FileSchema', related_name='schema_blocks', on_delete=models.CASCADE)
