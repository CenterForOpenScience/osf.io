from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class SchemaResponseBlock(ObjectIDMixin, BaseModel):

    # Match length for RegistrationSchemaBlockKey.registration_response_key
    schema_key = models.CharField(max_length=255)
    response = DateTimeAwareJSONField(null=True)

    # The RegistrationSchemaBlock that defines the question being answered
    source_block = models.ForeignKey('osf.RegistrationSchemaBlock', null=False)