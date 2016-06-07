from osf_models.utils.base import get_object_id
from osf_models.models.base import BaseModel
from django.db import models
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField

class MetaSchema(BaseModel):
    guid = models.CharField(max_length=255,
                            unique=True,
                            db_index=True,
                            default=get_object_id)
    name = models.CharField(max_length=255)
    schema = DatetimeAwareJSONField(default={})
    category = models.CharField(max_length=255)

    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = models.IntegerField()

    class Meta:
        unique_together = ('name', 'schema_version', 'guid')

    @property
    def _id(self):
        return self.guid

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

    @classmethod
    def get_prereg_schema(cls):
        return cls.get(
            name='Prereg Challenge',
            schema_version=2
        )
