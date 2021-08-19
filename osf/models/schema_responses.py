from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponses(ObjectIDMixin, BaseModel):

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    response_blocks = models.ManyToManyField('osf.schemaresponseblock', related_name='schema_response')

    revision_justification = models.CharField(max_length=2048, null=True)
    initiator = models.ForeignKey('OSFUser', null=False)
    submitted_timestamp = NonNaiveDateTimeField(null=True)

    @property
    def previous_version(self):
        return self.parent.schema_responses.filter(created__lt=self.created).order_by('created').first()
