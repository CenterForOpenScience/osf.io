# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.postgres.fields import ArrayField
import jsonschema

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.exceptions import ValidationValueError

from website.project.metadata.utils import create_jsonschema_from_metaschema

FORMBLOCK_TYPES = [
    ('string', 'string'),
    ('singleselect', 'singleselect'),
    ('multiselect', 'multiselect'),
    ('osf-author-import', 'osf-author-import'),
    ('osf-upload', 'osf-upload'),
    ('header', 'header'),
]

FORMBLOCK_SIZES = [
    ('sm', 'sm'),
    ('md', 'md'),
    ('lg', 'lg'),
    ('xl', 'xl'),
]


class AbstractSchema(ObjectIDMixin, BaseModel):
    name = models.CharField(max_length=255)
    schema = DateTimeAwareJSONField(default=dict)
    category = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)

    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = models.IntegerField()

    class Meta:
        abstract = True
        unique_together = ('name', 'schema_version')

    def __unicode__(self):
        return '(name={}, schema_version={}, id={})'.format(self.name, self.schema_version, self.id)


class RegistrationSchema(AbstractSchema):
    config = DateTimeAwareJSONField(blank=True, default=dict)

    @property
    def _config(self):
        return self.schema.get('config', {})

    @property
    def requires_approval(self):
        return self._config.get('requiresApproval', False)

    @property
    def fulfills(self):
        return self._config.get('fulfills', [])

    @property
    def messages(self):
        return self._config.get('messages', {})

    @property
    def requires_consent(self):
        return self._config.get('requiresConsent', False)

    @property
    def has_files(self):
        return self._config.get('hasFiles', False)

    @property
    def absolute_api_v2_url(self):
        path = '/schemas/registrations/{}/'.format(self._id)
        return api_v2_url(path)

    @classmethod
    def get_prereg_schema(cls):
        return cls.objects.get(
            name='Prereg Challenge',
            schema_version=2
        )

    def validate_metadata(self, metadata, reviewer=False, required_fields=False):
        """
        Validates registration_metadata field.
        """
        schema = create_jsonschema_from_metaschema(self.schema,
                                                   required_fields=required_fields,
                                                   is_reviewer=reviewer)
        try:
            jsonschema.validate(metadata, schema)
        except jsonschema.ValidationError as e:
            raise ValidationValueError(e.message)
        except jsonschema.SchemaError as e:
            raise ValidationValueError(e.message)
        return


class RegistrationFormBlock(ObjectIDMixin, BaseModel):
    class Meta:
        unique_together = ('schema', 'block_id')
        order_with_respect_to = 'schema'

    schema = models.ForeignKey('RegistrationSchema', related_name='form_blocks', on_delete=models.CASCADE)
    page = models.CharField(max_length=255)
    section = models.CharField(max_length=255, null=True)
    help_text = models.TextField()
    block_id = models.CharField(max_length=255, db_index=True)
    block_type = models.CharField(max_length=31, db_index=True, choices=FORMBLOCK_TYPES)
    block_text = models.TextField()
    size = models.CharField(max_length=2, null=True, choices=FORMBLOCK_SIZES)
    choices = ArrayField(models.TextField(), default=list)  # Longest on prod: >511 chars
    required = models.BooleanField(default=True)
