from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponses(ObjectIDMixin, BaseModel):

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    all_responses = models.ManyToManyField(SchemaResponseBlock)

    justification = models.CharField(max_length=2048, null=True)
    initiator = models.ForeignKey('OSFUser', null=False)
    submitted_timestamp = NonNaiveDateTimeField(null=True)
