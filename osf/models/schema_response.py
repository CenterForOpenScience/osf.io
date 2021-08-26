from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from framework.exceptions import PermissionsError

from osf.models import RegistrationSchemaBlock
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ApprovalsMachine
from osf.utils.workflows import ApprovalStates


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
        null=True
    )

    revision_justification = models.CharField(max_length=2048, null=True)
    submitted_timestamp = NonNaiveDateTimeField(null=True)
    pending_approvers = models.ManyToManyField('osf.osfuser', related_name='pending_submissions')
    reviews_state = models.CharField(
        choices=ApprovalStates.char_field_choices(),
        default=ApprovalStates.IN_PROGRESS.db_name,
        max_length=255
    )

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.machine = ApprovalsMachine(
            model=self,
            active_state=self.state,
            state_property_name='state'
        )

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

    @property
    def state(self):
        '''Property to translate between ApprovalState Enum and DB string.'''
        return ApprovalStates.from_db_name(self.reviews_state)

    @state.setter
    def state(self, new_state):
        self.reviews_state = new_state.db_name

    @property
    def is_moderated(self):
        '''Determine if this SchemaResponseResponse belong to a moderated resource'''
        return getattr(self.parent, 'is_moderated', False)

    @property
    def revisable(self):
        '''Controls what state the Response moves when rejected.

        True -> return to IN_PROGRESS
        False -> either ADMIN_REJECTED or MODERATOR_REJECTED
        '''
        return True

    @classmethod
    def create_initial_response(cls, initiator, parent, schema, justification=None):
        '''Create SchemaResponses and all initial SchemaResponseBlocks.

        This should only be called the first time SchemaResponses are created for
        a parent object. Every subsequent time new Responses are being created, they
        should be based on existing responses to simplify diffing between versions.
        '''
        assert not parent.schema_responses.exists()

        #TODO: consider validation to ensure SchemaResponses aren't using a different
        # schema than a parent object

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
        '''Create SchemaResponses using existing SchemaResponses as a starting point.

        On creation, the new SchemaResponses will share all of its response_blocks with the
        previous_version (as no responses have changed). As responses are updated through the
        new SchemaResponses, new SchemaResponseBlocks will be created/updated.
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

        This will raise a ValueError at the end if any unsupported keys are encountered.
        If you do not want any writes to persist if called with unsupported keys,
        make sure to call in an atomic context.
        '''
        # TODO: Add check for state once that stuff is here

        # make a local copy of the responses so we can pop with impunity
        # no need for deepcopy, since we aren't mutating responses
        updated_responses = dict(updated_responses)

        for block in self.response_blocks.all():
            # Remove values from updated_responses to help detect unsupported keys
            latest_response = updated_responses.pop(block.schema_key, None)
            if latest_response is None or latest_response == block.response:
                continue

            if not self._response_reverted(block, latest_response):
                self._update_response(block, latest_response)

        if updated_responses:
            raise ValueError(f'Encountered unexpected keys: {updated_responses.keys()}')

    def _response_reverted(self, current_block, latest_response):
        '''Handle the case where an answer is reverted over the course of editing a Response.
        '''
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

    def _validate_trigger(self, event_data):
        '''Any additional validation to confirm that a trigger is being used correctly.

        For SchemaResponses, use this to enforce correctness of the internal 'accept' shortcut
        and to confirm that the provided user has permission to execute the trigger.
        '''
        # Restrictions on calls from PENDING_MODERATION and IN_PROGRESS states are handled by API
        if self.state is not ApprovalStates.UNAPPROVED:
            return

        user = event_data.kwargs.get('user')
        trigger = event_data.event.name
        # Allow "accept" witn o user from an UNAPPROVED state as an OSF-internal shortcut
        if not user and trigger != 'accept':
            raise ValueError(f'Trigger "{trigger}" must pass the user who invoked it"')

        # 'approve' and 'reject' triggers must supply a user
        if trigger in {'approve', 'reject'} and user not in self.pending_approvers.all():
            raise PermissionsError(f'{user} is not a pending approver on this submission')

    def _on_submit(self, event_data):
        '''Add the provided approvers to pending_approvers and set the submitted_timestamp.'''
        approvers = event_data.kwargs.get('required_approvers', None)
        if not approvers:
            raise ValueError(
                'Cannot submit SchemaResponses for review with no required approvers'
            )
        self.pending_approvers.set(approvers)
        self.submitted_timestamp = timezone.now()

    def _on_approve(self, event_data):
        '''Remove the user from pending_approvers; call accept when no approvers remain.'''
        approving_user = event_data.kwargs.get('user', None)
        self.pending_approvers.remove(approving_user)
        if not self.pending_approvers.exists():
            self.accept(user=approving_user)

    def _on_complete(self, event_data):
        '''No special logic on complete for SchemaResponses'''
        pass

    def _on_reject(self, event_data):
        '''Clear out pending_approvers to start fresh on resubmit.'''
        self.pending_approvers.clear()

    def _save_transition(self, event_data):
        '''Save changes here and write the action.'''
        self.save()
