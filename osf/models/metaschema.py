# -*- coding: utf-8 -*-
from django.db import models
import jsonschema

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.exceptions import ValidationValueError

from website.project.metadata.utils import create_jsonschema_from_metaschema


class AbstractSchema(ObjectIDMixin, BaseModel):
    name = models.CharField(max_length=255)
    schema = DateTimeAwareJSONField(default=dict)
    category = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)  # whether or not the schema accepts submissions
    visible = models.BooleanField(default=True)  # whether or not the schema should be visible in the API and registries search

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
            raise ValidationValueError(e.message)
        except jsonschema.SchemaError as e:
            raise ValidationValueError(e.message)
        return
