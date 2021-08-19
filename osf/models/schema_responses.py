from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from framework.exceptions import PermissionsError

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ApprovalsMachine
from osf.utils.workflows import ApprovalStates


class SchemaResponses(ObjectIDMixin, BaseModel):

    schema = models.ForeignKey('osf.registrationschema')
    response_blocks = models.ManyToManyField('osf.schemaresponseblock')
    initiator = models.ForeignKey('osf.osfuser', null=False)

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
    def state(self):
        return ApprovalStates.from_db_name(self.reviews_state)

    @state.setter
    def state(self, new_state):
        self.reviews_state = new_state.db_name

    @property
    def is_moderated(self):
        '''Determine if these Responses belong to a moderated resource'''
        return getattr(self.parent, 'is_moderated', False)

    @property
    def revisable(self):
        '''Controls what state the responses move to if they are rejected.

        True -> return to IN_PROGRESS
        False -> either ADMIN_REJECTED or MODERATOR_REJECTED
        '''
        return True

    def _validate_trigger(self, event_data):
        '''All additional validation to confirm that a trigger is being used correctly.

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
        self.save()
