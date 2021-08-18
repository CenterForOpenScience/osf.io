from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class SchemaResponseBlock(ObjectIDMixin, BaseModel):

    # The SchemaResponses version where this response originated
    source_revision = models.ForeignKey('osf.SchemaResponses', null=False)
    # The RegistrationSchemaBlock that defines the question being answered
    source_block = models.ForeignKey('osf.RegistrationSchemaBlock', null=False)

    # Should match source_block.registration_response_key
    schema_key = models.CharField(max_length=255)
    answer = models.TextField()

    class Meta:
        unique_together = ('source_revision', 'source_block')
