from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class SchemaResponseBlock(ObjectIDMixin, BaseModel):

    # The SchemaResponses instance where this response originated
    source_schema_response = models.ForeignKey(
        'osf.SchemaResponse',
        null=False,
        related_name='updated_response_blocks'
    )
    # The RegistrationSchemaBlock that defines the question being answered
    source_schema_block = models.ForeignKey('osf.RegistrationSchemaBlock', null=False)

    # Should match source_block.registration_response_key
    schema_key = models.CharField(max_length=255)
    response = DateTimeAwareJSONField(blank=True, null=True)

    class Meta:
        unique_together = ('source_schema_response', 'source_schema_block')
