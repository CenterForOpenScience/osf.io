from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models import RegistrationSchemaBlock
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponse(ObjectIDMixin, BaseModel):
    '''Collects responses for a schema associated with a parent object.

<<<<<<< HEAD
    SchemaResponses manages to creation, surfacing, updating, and approval of
    "responses" to the questions on a Registration schema (for example).

    Individual answers are stored in SchemaResponseBlocks and aggregated here
    via the response_blocks M2M relationship.

    SchemaResponseBlocks can be shared across multiple SchemaResponses, but
    each SchemaResponseBlock links to the SchemaResponse where it originated.
    These are referenced on the SchemaResponses using the revised_response_blocks manager.
    This allows SchemaResponses to also serve as a revision history when
    users submit updates to the schema form on a given parent object.
    '''
    schema = models.ForeignKey('osf.RegistrationSchema')
    response_blocks = models.ManyToManyField('osf.SchemaResponseBlock')
    initiator = models.ForeignKey('osf.OsfUser', null=False)
    previous_response = models.ForeignKey(
        'osf.SchemaResponse',
        related_name='updated_response',
        null=True
    )

    revision_justification = models.CharField(max_length=2048, null=True)
    submitted_timestamp = NonNaiveDateTimeField(null=True)

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

    @classmethod
    def create_initial_responses(cls, initiator, parent, schema, justification=None):
        '''Create SchemaResponses and all initial SchemaResponseBlocks.

        This should only be called the first time SchemaResponses are created for
        a parent object. Every subsequent time new Responses are being created, they
        should be based on existing responses to simplify diffing between versions.
        '''
        assert not parent.schema_responses.exists()

        #TODO: consider validation to ensure SchemaResponses aren't using a different
        # schema than a parent object

        new_responses = cls(
            parent=parent,
            schema=schema,
            initiator=initiator,
            revision_justification=justification or ''
        )
        new_responses.save()

        question_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema,
            registration_response_key__isnull=False
        )
        for source_block in question_blocks:
            new_response_block = SchemaResponseBlock.objects.create(
                source_revision=new_responses,
                source_block=source_block,
                schema_key=source_block.registration_response_key,
            )
            new_response_block.save()
            new_responses.response_blocks.add(new_response_block)

        return new_responses

    @classmethod
    def create_from_previous_responses(cls, initiator, previous_responses, justification=None):
        '''Create SchemaResponses using existing SchemaResponses as a starting point.

        On creation, the new SchemaResponses will share all of its response_blocks with the
        previous_version (as no responses have changed). As responses are updated through the
        new SchemaResponses, new SchemaResponseBlocks will be created/updated.
        '''

        # TODO confirm that no other non-Approved responses exist
        new_responses = cls(
            parent=previous_responses.parent,
            schema=previous_responses.schema,
            initiator=initiator,
            revision_justification=justification or ''
        )
        new_responses.save()
        new_responses.response_blocks.add(*previous_responses.response_blocks.all())
        return new_responses

    def update_responses(self, updated_responses):
        '''
        Args
        updated_responses: All of the latest responses for the schema in JSON format
           (i.e. what will be returned by self.revision_responses following this call)
        '''
        # TODO: Add check for state once that stuff is here
        # TODO: Handle the case where an updated response is reverted
        for block in self.response_blocks.all():
            # Remove values from updated_responses to help detect unsupported keys
            latest_response = updated_responses.pop(block.schema_key)
            if latest_response != block.responses:
                self._update_response(block, latest_response)

        if updated_responses:
            raise ValueError(f'Encountered unexpected keys: {updated_responses.keys()}')

    def _update_response(self, current_block, latest_response):
        '''Create/update a SchemaResponseBlock with a new answer.'''
        # Update the block in-place if it's already part of this revision
        if current_block.source_revision == self:
            current_block.response = latest_response
            current_block.save()
        # Otherwise, create a new block and swap out the entries in response_blocks
        else:
            revised_block = SchemaResponseBlock.objects.create(
                source_revision=self,
                source_block=current_block.source_block,
                schema_key=current_block.schema_key,
                respone=latest_response
            )

            revised_block.save()
            self.response_blocks.remove(current_block)
            self.response_blocks.add(revised_block)
