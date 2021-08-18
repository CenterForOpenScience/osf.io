from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
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
            active_state=self.approval_state,
            state_property_name='state'
        )

    @property
    def state(self):
        return ApprovalStates.from_db_name(self.state)

    @state.setter
    def state(self, new_state):
        self.state = new_state.db_name

    @property
    def is_moderated(self):
        return getattr(self.parent, 'is_moderated', False)

    @property
    def revisable(self):
        '''Controls what happens when responses are rejected'''
        return True

    def _validate_trigger(self, event_data):
        '''All additional validation to confirm that a trigger is being used correctly.

        For SchemaResponses, use this to enforce correctness of the internal 'accept' shortcut.
        '''
        # Allow 'accept' without a user only to bypass internal
        user = event_data.get('user')
        trigger = event_data.get('action')
        if not user and trigger != 'accept' and self.state is not ApprovalStates.UNAPPROVED:
            raise ValueError(f'Trigger "{trigger}" must pass the user who invoked it"')

        if self.state is ApprovalStates.UNAPPROVED and not self.pending_approvers.get(user):
            raise RuntimeError(f'{user} is not a pending approver on this submission')

    def _on_submit(self, event_data):
        approvers = event_data.get('required_approvers', None)
        if not approvers:
            raise ValueError(
                'Cannot submit SchemaResponses for review with no required approvers'
            )
        self.pending_approvers.set(approvers)

    def _on_approve(self, event_data):
        approving_user = event_data['user']
        self.pending_approvers.remove(approving_user)
        if not self.pending_approvers.exists():
            self.accept()

    def _on_reject(self, event_data):
        self.pending_approvers.clear()

    def _save_transition(self, event_data):
        pass
