from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class SchemaResponseBlock(ObjectIDMixin, BaseModel):

    # The RegistrationSchemaBlock that defines the question being answered
    source_block = models.ForeignKey('osf.RegistrationSchemaBlock', null=False)
    # The SchemaResponses version where this response originated
    source_revision = models.ForeignKey('osf.SchemaResponses', null=False)

    # Should match source_block.registration_response_key
    schema_key = models.CharField(max_length=255)
    answer = models.TextField()
