from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models import RegistrationSchemaBlock, SchemaResponseBlock
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

    @classmethod
    def create_initial_responses(cls, initiator, parent, schema, justification=None):
        assert not parent.schema_responses.exists()

        #TODO: consider validation to ensure SchemaResponses aren't using a different
        # schema than a parent object

        new_responses = cls(
            parent=parent,
            schema=schema,
            initiator=initiator,
            justification=justification or ''
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
            new_responses.resposne_blocks.add(new_response_block)

    @classmethod
    def create_from_previous_responses(cls, initiator, previous_responses, justification=None):
        '''Create a new SchemaResponses object referencing existing SchemaResponseBlocks.

        New response blocks will be created as updated answers are proveded
        '''
        # TODO confirm that no other non-Approved responses exist
        new_responses = cls(
            parent=previous_responses.parent,
            schema=previous_responses.schema,
            initiator=initiator,
            revision_justification=justification or ''
        )
        new_responses.response_blocks.add(*previous_responses.response_blocks)

    def update_responses(self, updated_responses):
        '''
        Args
        updated_responses: All of the latest responses for the schema in JSON format
           (i.e. what will be returned by self.revision_responses following this call)
        '''
        # TODO: Add check for state once that stuff is here
        for block in self.response_blocks:
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
            self.save()  # is this needed?
