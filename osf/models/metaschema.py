# -*- coding: utf-8 -*-
from django.db import models
import waffle
import jsonschema

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.validators import RegistrationResponsesValidator
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.exceptions import ValidationValueError, ValidationError

from website.project.metadata.utils import create_jsonschema_from_metaschema
from osf.features import EGAP_ADMINS


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


def allow_egap_admins(queryset, request):
    """
    Allows egap admins to see EGAP registrations as visible, should be deleted when when the EGAP registry goes
    live.
    """
    if hasattr(request, 'user') and not waffle.flag_is_active(request, EGAP_ADMINS):
        return queryset.exclude(name='EGAP Registration')
    return queryset

class AbstractSchemaManager(models.Manager):

    def get_latest_version(self, name):
        """
        Return the latest version of the given schema
        :param str only_active: Only returns the latest active schema
        :return schema
        """
        return self.filter(name=name).order_by('schema_version').last()

    def get_latest_versions(self, request=None, invisible=False):
        """
        Return the latest version of the given schema

        :param request: the request object needed for waffling
        :return: queryset
        """
        queryset = self.order_by('name', '-schema_version').distinct('name')

        if not invisible:
            queryset = queryset.filter(visible=True)

        if request:
            return allow_egap_admins(queryset, request)

        return queryset

class AbstractSchema(ObjectIDMixin, BaseModel):
    name = models.CharField(max_length=255)
    schema = DateTimeAwareJSONField(default=dict)
    category = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)  # whether or not the schema accepts submissions
    visible = models.BooleanField(default=True)  # whether or not the schema should be visible in the API and registries search

    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = models.IntegerField()

    objects = AbstractSchemaManager()

    class Meta:
        abstract = True
        unique_together = ('name', 'schema_version')

    def __unicode__(self):
        return '(name={}, schema_version={}, id={})'.format(self.name, self.schema_version, self.id)


class RegistrationSchema(AbstractSchema):
    config = DateTimeAwareJSONField(blank=True, default=dict)
    description = models.TextField(null=True, blank=True)
    providers = models.ManyToManyField(
        'RegistrationProvider',
        related_name='schemas',
        blank=True
    )

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
            for page in self.schema['pages']:
                for question in page['questions']:
                    if e.relative_schema_path[0] == 'required':
                        raise ValidationError(
                            'For your registration the \'{}\' field is required'.format(question['title'])
                        )
                    elif e.relative_schema_path[0] == 'additionalProperties':
                        raise ValidationError(
                            'For your registration the \'{}\' field is extraneous and not permitted in your response.'.format(question['qid'])
                        )
                    elif e.relative_path[0] == question['qid']:
                        if 'options' in question:
                            raise ValidationError(
                                'For your registration your response to the \'{}\' field is invalid, your response must be one of the provided options.'.format(
                                    question['title'],
                                ),
                            )
                        if 'title' in question:
                            raise ValidationError(
                                'For your registration your response to the \'{}\' field is invalid.'.format(question['title']),
                            )
                        raise ValidationError(
                            'For your registration your response to the field with qid: \'{}\' is invalid.'.format(question['qid']),
                        )
            raise ValidationError(e)
        except jsonschema.SchemaError as e:
            raise ValidationValueError(e)
        return

    def validate_registration_responses(self, registration_responses, required_fields=False):
        """Validates `registration_responses` against this schema (using `schema_blocks`).
        Raises `ValidationError` if invalid. Otherwise, returns True.
        """
        validator = RegistrationResponsesValidator(self.schema_blocks.all(), required_fields)
        return validator.validate(registration_responses)


class FileMetadataSchema(AbstractSchema):

    @property
    def absolute_api_v2_url(self):
        path = '/schemas/files/{}/'.format(self._id)
        return api_v2_url(path)


class RegistrationSchemaBlock(ObjectIDMixin, BaseModel):
    class Meta:
        order_with_respect_to = 'schema'
        unique_together = ('schema', 'registration_response_key')

    schema = models.ForeignKey('RegistrationSchema', related_name='schema_blocks', on_delete=models.CASCADE)
    help_text = models.TextField()
    example_text = models.TextField(null=True)
    # Corresponds to a key in DraftRegistration.registration_responses dictionary
    registration_response_key = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    # A question can be split into multiple schema blocks, but are linked with a schema_block_group_key
    schema_block_group_key = models.CharField(max_length=24, db_index=True, null=True)
    block_type = models.CharField(max_length=31, db_index=True, choices=SCHEMABLOCK_TYPES)
    display_text = models.TextField()
    required = models.BooleanField(default=False)

    @property
    def absolute_api_v2_url(self):
        path = '{}schema_blocks/{}/'.format(self.schema.absolute_api_v2_url, self._id)
        return api_v2_url(path)

    def save(self, *args, **kwargs):
        """
        Allows us to use a unique_together constraint, so each "registration_response_key"
        only appears once for every registration schema.  To do this, we need to save
        empty "registration_response_key"s as null, instead of an empty string.
        """
        self.registration_response_key = self.registration_response_key or None
        return super(RegistrationSchemaBlock, self).save(*args, **kwargs)
