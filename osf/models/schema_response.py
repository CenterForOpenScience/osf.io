from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models import RegistrationSchemaBlock
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.fields import NonNaiveDateTimeField


class SchemaResponse(ObjectIDMixin, BaseModel):
    '''Collects responses for a schema associated with a parent object.

    SchemaResponse manages to creation, surfacing, updating, and approval of
    "responses" to the questions on a Registration schema (for example).

    Individual answers are stored in SchemaResponseBlocks and aggregated here
    via the response_blocks M2M relationship.

    SchemaResponseBlocks can be shared across multiple SchemaResponse, but
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
        return set(revised_keys)

    @classmethod
    def create_initial_response(cls, initiator, parent, schema=None, justification=None):
        '''Create SchemaResponse and all initial SchemaResponseBlocks.

        This should only be called the first time SchemaResponses are created for
        a parent object. Every subsequent time new Responses are being created, they
        should be based on existing responses to simplify diffing between versions.
        '''
        assert not parent.schema_responses.exists()

        # TODO: Decide on a fixed property/field name that parent types should implement
        # to access a supported schema. Just use registration_schema for now.
        parent_schema = parent.registration_schema
        schema = schema or parent_schema
        if not schema:
            raise ValueError('Must pass a schema if parent resource does not define one.')
        if schema != parent_schema:
            raise ValueError(
                f'Provided schema ({schema.name}) does not match '
                f'schema on parent ({parent_schema.name})'
            )

        new_response = cls(
            parent=parent,
            schema=schema,
            initiator=initiator,
            revision_justification=justification or ''
        )
        new_response.save()

        question_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema,
            registration_response_key__isnull=False
        )
        for source_block in question_blocks:
            new_response_block = SchemaResponseBlock.objects.create(
                source_schema_response=new_response,
                source_schema_block=source_block,
                schema_key=source_block.registration_response_key,
            )
            new_response_block.save()
            new_response.response_blocks.add(new_response_block)

        return new_response

    @classmethod
    def create_from_previous_response(cls, initiator, previous_response, justification=None):
        '''Create a SchemaResponse using an existing SchemaResponse as a starting point.

        On creation, the new SchemaResponses will share all of its response_blocks with the
        previous_version (as no responses have changed). As responses are updated via
        response.update_responses, new SchemaResponseBlocks will be created/updated as apporpriate.
        '''

        # TODO confirm that no other non-Approved responses exist
        new_response = cls(
            parent=previous_response.parent,
            schema=previous_response.schema,
            initiator=initiator,
            previous_response=previous_response,
            revision_justification=justification or ''
        )
        new_response.save()
        new_response.response_blocks.add(*previous_response.response_blocks.all())
        return new_response

    def update_responses(self, updated_responses):
        '''Updates any response_blocks with keys listed in updated_responses

        If this is the first time a given key has been updated on this SchemaResponse, a
        new SchemaResponseBlock (with source_schema_response=self) will be created to hold the
        answer and added to response_blocks, and the outdated response_block entry for that key
        (inherited from the previous_response) will be removed from response_blocks.

        If a previously updated response is udpated again, the existing entry in response_blocks
        for that key will have its "response" field updated to the new value.

        If a previously updated response has its answer reverted to the previous_response's answer,
        the previously created SchemaResponseBlock will be deleted, and the previous_response's
        response_block for that key will be restored to self's response_blocks.

        This will raise a ValueError at the end if any unsupported keys are encountered.
        If you do not want any writes to persist if called with unsupported keys,
        make sure to call in an atomic context.
        '''
        # TODO: Add check for state once that stuff is here
        if not updated_responses:
            return

        # make a local copy of the responses so we can pop with impunity
        # no need for deepcopy, since we aren't mutating dictionary values
        updated_responses = dict(updated_responses)

        for block in self.response_blocks.all():
            # Remove values from updated_responses to help detect unsupported keys
            latest_response = updated_responses.pop(block.schema_key, None)
            if latest_response is None or latest_response == block.response:
                continue

            if not self._response_reverted(block, latest_response):
                self._update_response(block, latest_response)

        if updated_responses:
            raise ValueError(f'Encountered unexpected keys: {",".join(updated_responses.keys())}')

    def _response_reverted(self, current_block, latest_response):
        '''Handle the case where an answer is reverted over the course of editing a Response.'''
        if not self.previous_response:
            return False

        previous_response_block = self.previous_response.response_blocks.get(
            schema_key=current_block.schema_key
        )
        if latest_response != previous_response_block.response:
            return False

        current_block.delete()
        self.response_blocks.add(previous_response_block)
        return True

    def _update_response(self, current_block, latest_response):
        '''Create/update a SchemaResponseBlock with a new answer.'''
        # Update the block in-place if it's already part of this revision
        if current_block.source_schema_response == self:
            current_block.response = latest_response
            current_block.save()
        # Otherwise, create a new block and swap out the entries in response_blocks
        else:
            revised_block = SchemaResponseBlock.objects.create(
                source_schema_response=self,
                source_schema_block=current_block.source_schema_block,
                schema_key=current_block.schema_key,
                response=latest_response
            )

            revised_block.save()
            self.response_blocks.remove(current_block)
            self.response_blocks.add(revised_block)
