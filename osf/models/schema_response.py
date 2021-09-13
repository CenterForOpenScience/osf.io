from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from framework.exceptions import PermissionsError

from osf.exceptions import PreviousPendingSchemaResponseError, SchemaResponseStateError
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import RegistrationSchemaBlock
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ApprovalsMachine
from osf.utils.workflows import ApprovalStates, SchemaResponseTriggers


class SchemaResponse(ObjectIDMixin, BaseModel):
    '''Collects responses for a schema associated with a parent object.

    SchemaResponse manages the creation, surfacing, updating, and approval of
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
        blank=True
    )

    revision_justification = models.CharField(max_length=2048, null=True, blank=True)
    submitted_timestamp = NonNaiveDateTimeField(null=True, blank=True)
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

    # Attribute for controlling flow from 'reject' triggers on the state machine.
    # True -> IN_PROGRESS
    # False -> [MODERATOR_]REJECTED
    revisable = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.approvals_state_machine = ApprovalsMachine(
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
            raise ValueError(
                'Must pass a schema when creating SchemaResponse if '
                'parent resource does not define one.'
            )
        if schema != parent_schema:
            raise ValueError(
                f'Provided schema ({schema.name}) does not match '
                f'schema on parent resource ({parent_schema.name})'
            )

        new_response = cls(
            parent=parent,
            schema=schema,
            initiator=initiator,
            revision_justification=justification or '',
            submitted_timestamp=None,
            previous_response=None,
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

        A new SchemaResponse cannot be created for a given parent object if it already has another
        SchemaResponse in a non-APPROVED state.
        '''
        # Cannot create new response if parent has another response in-progress or pending approval
        parent = previous_response.parent
        if parent.schema_responses.exclude(reviews_state=ApprovalStates.APPROVED.db_name).exists():
            raise PreviousPendingSchemaResponseError(
                f'Cannot create new SchemaResponse for {parent} because {parent} already '
                'has non-terminal SchemaResponse'
            )

        new_response = cls(
            parent=parent,
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

        Only SchemaResponses in state IN_PROGRESS can have their responses updated.

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
        if self.state is not ApprovalStates.IN_PROGRESS:
            raise SchemaResponseStateError(
                f'SchemaResponse with id {self._id}  has state {self.reviews_state}. '
                'Must have state "in_progress" to update responses'
            )

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
            raise ValueError(
                'Encountered unexpected keys while trying to update responses for '
                f'SchemaResponse with id [{self._id}]: {", ".join(updated_responses.keys())}'
            )

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

    def delete(self, *args, **kwargs):
        if self.state is not ApprovalStates.IN_PROGRESS:
            raise SchemaResponseStateError(
                'Cannot delete SchemaResponse with id [{self.id}]. In order to delete, '
                'state must be "in_progress", but is "{self.reviews_state}" instead.'
            )
        super().delete(*args, **kwargs)

# *** Callbcks in support of ApprovalsMachine ***

    def _validate_trigger(self, event_data):
        '''Any additional validation to confirm that a trigger is being used correctly.

        For SchemaResponses, use this to confirm that the provided user has permission to
        execute the trigger, including enforcing correct usage of the internal "accept" shortcut.
        '''
        user = event_data.kwargs.get('user')
        trigger = event_data.event.name

        # The only valid case for not providing a user is the internal accept shortcut
        # See _validate_accept_trigger docstring for more information
        if user is None and not (trigger == 'accept' and self.state is ApprovalStates.UNAPPROVED):
            raise ValueError(
                f'Trigger {trigger} from state {self.state} for '
                f'SchemaResponse with id [{self.id}] must be called with a user.'
            )

        trigger_specific_validator = getattr(self, f'_validate_{trigger}_trigger')
        trigger_specific_validator(user)

    def _validate_submit_trigger(self, user):
        """Validate usage of the "submit" trigger on the underlying ApprovalsMachine.

        Only admins on the parent resource can submit the SchemaResponse for review.

        submit can only be called from IN_PROGRESS, calling from any other state will
        result in a MachineError prior to this validation.
        """
        if not self.parent.is_admin_contributor(user):
            raise PermissionsError(
                f'User {user} is not an admin contributor on parent resource {self.parent} '
                f'and does not have permission to "submit" SchemaResponse with id [{self.id}]'
            )

    def _validate_approve_trigger(self, user):
        """Validate usage of the "approve" trigger on the underlying ApprovalsMachine

        Only users listed in self.pending_approvers can approve.

        "approve" can only be invoked from UNAPPROVED, calling from any other state will
        result in a MachineError prior to this validation.
        """
        if user not in self.pending_approvers.all():
            raise PermissionsError(
                f'User {user} is not a pending approver for SchemaResponse with id [{self.id}]'
            )

    def _validate_accept_trigger(self, user):
        """Validate usage of the "accept" trigger on the underlying ApprovalsMachine

        "accept" has three valid usages:
        First, "accept" is called from within the"approve" trigger once all required approvals
        have been granted. This call should receive the user who issued the final "approve"
        so that the correct SchemaResponseAction can be logged.

        Secone, moderators "accept" a SchemaResponse if it belongs to a moderated parent resource.
        In this case, the user must have the correct permission on the parent's provider.

        Finally, "accept" can be called without a user in order to bypass the need for approvals
        (the "internal accept shortcut") to make life easier for OSF scripts and utilities.

        "accept" can only be invoked from UNAPPROVED and PENDING_MODERATION, calling from any
        other state will result in a MachineError prior to this validation.
        """
        if self.state is ApprovalStates.UNAPPROVED:
            # user = None -> internal accept shortcut
            # not self.pending_approvers.exists() -> called from within "approve"
            if user is None or not self.pending_approvers.exists():
                return
            raise ValueError(
                'Invalid usage of "accept" trigger from UNAPPROVED state '
                f'against SchemaResponse with id [{self.id}]'
            )

        if not user.has_perm('accept_submissions', self.parent.provider):
            raise PermissionsError(
                f'User {user} is not a moderator on {self.parent.provider} and does not '
                f'have permission to "accept" SchemaResponse with id [{self.id}]'
            )

    def _validate_reject_trigger(self, user):
        """Validate usage of the "reject" trigger on the underlying ApprovalsMachine

        "reject" must be called by a pending approver or a moderator, depending on the state.

        "reject" can only be invoked from UNAPPROVED and PENDING_MODERATION, calling from any
        other state will result in a MachineError prior to this validation.
        """
        if self.state is ApprovalStates.UNAPPROVED:
            if user not in self.pending_approvers.all():
                raise PermissionsError(
                    f'User {user} is not a pending approver for SchemaResponse with id [{self.id}]'
                )
            return

        if not user.has_perm('reject_submissions', self.parent.provider):
            raise PermissionsError(
                f'User {user} is not a modrator on {self.parent.provider} and does not '
                f'have permission to "reject" SchemaResponse with id [{self.id}]'
            )

    def _on_submit(self, event_data):
        '''Add the provided approvers to pending_approvers and set the submitted_timestamp.'''
        approvers = event_data.kwargs.get('required_approvers', None)
        if not approvers:
            raise ValueError(
                f'Cannot submit SchemaResponses with id [{self.id}] '
                'for review with no required approvers'
            )
        self.pending_approvers.set(approvers)
        self.submitted_timestamp = timezone.now()

    def _on_approve(self, event_data):
        '''Remove the user from pending_approvers; call accept when no approvers remain.'''
        approving_user = event_data.kwargs.get('user', None)
        self.pending_approvers.remove(approving_user)
        if not self.pending_approvers.exists():
            self.accept(**event_data.kwargs)

    def _on_complete(self, event_data):
        '''Clear out any lingering pending_approvers in the case of an internal accept.'''
        self.pending_approvers.clear()

    def _on_reject(self, event_data):
        '''Clear out pending_approvers to start fresh on resubmit.'''
        self.pending_approvers.clear()

    def _save_transition(self, event_data):
        '''Save changes here and write the action.'''
        self.save()
        # Skip writing the final UNAPPROVED -> UNAPPROVED transition and wait for the accept trigger
        if self.state is ApprovalStates.UNAPPROVED and not self.pending_approvers.exists():
            return

        from_state = ApprovalStates[event_data.transition.source]
        to_state = self.state
        trigger = SchemaResponseTriggers.from_transition(from_state, to_state)
        self.actions.create(
            from_state=from_state.db_name,
            to_state=to_state.db_name,
            trigger=trigger.db_name,
            creator=event_data.kwargs.get('user', self.initiator),
            comment=event_data.kwargs.get('comment', '')
        )
