# -*- coding: utf-8 -*-
from django.db import models
import jsonschema

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.exceptions import ValidationValueError, ValidationError

from website.project.metadata.utils import create_jsonschema_from_metaschema


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
            for page in self.schema['pages']:
                for question in page['questions']:
                    if e.relative_schema_path[0] == 'required':
                        raise ValidationError(
                            'For your registration the \'{}\' field is required'.format(question['title'])
                        )
                    elif e.relative_path[0] == question['qid']:
                        if 'options' in question:
                            raise ValidationError(
                                'For your registration the \'{}\' field is invalid, your response must be one of the provided options.'.format(
                                    question['title'],
                                ),
                            )
                        raise ValidationError(
                            'For your registration the \'{}\' field is invalid.'.format(question['title']),
                        )
            raise ValidationError(e.message)
        except jsonschema.SchemaError as e:
            raise ValidationValueError(e.message)
        return
