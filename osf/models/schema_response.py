from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponse(ObjectIDMixin, BaseModel):
    '''Collects responses for a schema associated with a parent object.

    SchemaResponse manages to creation, surfacing, updating, and approval of
    "responses" to the questions on a Registration schema (for example).

    Individual answers are stored in SchemaResponseBlocks and aggregated here
    via the response_blocks M2M relationship.

    SchemaResponseBlocks can be shared across multiple SchemaResponses, but
    each SchemaResponseBlock links to the SchemaResponse where it originated.
    These are referenced on the SchemaResponse using the updated_response_blocks manager.
    This allows SchemaResponses to also serve as a revision history when
    users submit updates to the schema form on a given parent object.
    '''
    schema = models.ForeignKey('osf.RegistrationSchema')
    response_blocks = models.ManyToManyField('osf.SchemaResponseBlock')
    initiator = models.ForeignKey('osf.OsfUser', null=False)
    previous_response = models.ForeignKey(
        'osf.SchemaResponse',
        related_name='updated_response',
        null=True,
        blank=True,
    )

    revision_justification = models.CharField(max_length=2048, null=True, blank=True)
    submitted_timestamp = NonNaiveDateTimeField(null=True, blank=True)
    pending_approvers = models.ManyToManyField('osf.osfuser', related_name='pending_submissions')

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    @property
    def all_responses(self):
        '''Surfaces responses from response_blocks in a dictionary format'''
        formatted_responses = {
            response_block.schema_key: response_block.response
            for response_block in self.response_blocks.all()
        }
        return formatted_responses

    @property
    def updated_response_keys(self):
        '''Surfaces the keys of responses_blocks added in this revision.'''
        revised_keys = self.updated_response_blocks.values_list('schema_key', flat=True)
        return list(revised_keys)
