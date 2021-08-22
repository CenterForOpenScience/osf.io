from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField
from osf.exceptions import SchemaResponseStateError


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
    def previous_version(self):
        return self.parent.schema_responses.filter(created__lt=self.created).order_by('created').first()

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
        from osf.models import RegistrationSchemaBlock, SchemaResponseBlock

        assert not parent.schema_responses.exists(), \
            SchemaResponseStateError('Cannot use this method when schema response has parent.')

        #TODO: consider validation to ensure SchemaResponses aren't using a different
        # schema than a parent object

        new_responses = cls(
            parent=parent,
            schema=schema,
            initiator=initiator,
            revision_justification=justification or '',
            submitted_timestamp=timezone.now()
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
                response={},
            )
            new_response_block.save()
            new_responses.response_blocks.add(new_response_block)

        return new_responses

    @classmethod
    def create_from_previous_schema_response(cls, initiator, previous_schema_response, justification=None):
        '''Create a new SchemaResponses object referencing existing SchemaResponseBlocks.

        New response blocks will be created as updated answers are proveded
        '''
        # TODO confirm that no other non-Approved responses exist
        new_responses = cls(
            parent=previous_schema_response.parent,
            schema=previous_schema_response.schema,
            initiator=initiator,
            revision_justification=justification or ''
        )
        new_responses.save()
        new_responses.response_blocks.add(*previous_schema_response.response_blocks.all())

        return new_responses

    def update_responses(self, updated_responses):
        '''
        Args
        updated_responses: All of the latest responses for the schema in JSON format
           (i.e. what will be returned by self.revision_responses following this call)
        '''
        # TODO: Add check for state once that stuff is here
        for block in self.response_blocks.all():
            # Remove values from updated_responses to help detect unsupported keys
            try:
                latest_response = updated_responses.pop(block.schema_key)
            except KeyError:
                raise ValueError(f'payload requires key: {block.schema_key}')

            if latest_response != block.response:
                self._update_response(block, latest_response)

        if updated_responses:
            raise ValueError(f'Encountered unexpected keys: {", ".join(list(updated_responses.keys()))}')

    def _update_response(self, current_block, latest_response):
        '''Create/update a SchemaResponseBlock with a new answer.'''
        from osf.models import SchemaResponseBlock

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
                response=latest_response
            )

            revised_block.save()
            self.response_blocks.remove(current_block)
            self.response_blocks.add(revised_block)
            self.save()  # is this needed?
