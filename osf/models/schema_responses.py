from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponses(ObjectIDMixin, BaseModel):

    schema = models.ForeignKey('osf.registrationschema')
    response_blocks = models.ManyToManyField('osf.schemaresponseblock')
    initiator = models.ForeignKey('osf.osfuser', null=False)

    revision_justification = models.CharField(max_length=2048, null=True)
    submitted_timestamp = NonNaiveDateTimeField(null=True)

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    @property
    def revision_responses(self):
        '''Surfaces responses from response_blocks in a dictionary format'''
        formatted_responses = {
            response_block.schema_key: response_block.response
            for response_block in self.response_blocks.all()
        }
        return formatted_responses

    @property
    def revised_responses(self):
        '''Surfaces the keys of responses_blocks added in this revision.'''
        revised_keys = self.revised_response_blocks.values_list('schema_key', flat=True)
        return list(revised_keys)
