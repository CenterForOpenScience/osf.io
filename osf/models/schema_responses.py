from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ApprovalsMachine
from osf.utils.workflows import ApprovalStates


class SchemaResponses(ObjectIDMixin, BaseModel):

    schema = models.ForeignKey('osf.registrationschema')
    all_responses = models.ManyToManyField('osf.schemaresponseblock')
    initiator = models.ForeignKey('osf.osfuser', null=False, related_name='initaited_responses')

    submitted_timestamp = NonNaiveDateTimeField(null=True)
    pending_approvers = models.ManyToManyField('osf.osfuser', related_name='pending_submissions')
    state = models.CharField(
        choices=ApprovalStates.char_field_choices(),
        default=ApprovalStates.IN_PROGRESS.db_name,
        max_length=255
    )

    justification = models.CharField(max_length=2048, null=True)

    # Allow schema responses for non-Registrations
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent = GenericForeignKey('content_type', 'object_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.machine = ApprovalsMachine(
            model=self,
            active_state=self.approval_state,
            state_property_name='approval_state'
        )

    @property
    def approval_state(self):
        return ApprovalStates.from_db_name(self.state)

    @approval_state.setter
    def approval_state(self, new_state):
        self.state = new_state.db_name

    @property
    def is_moderated(self):
        return getattr(self.parent, 'is_moderated', False)

    @property
    def revisable(self):
        '''Controls what happens when responses are rejected'''
        return True

    def _validate_trigger(self, event_data):
        # Delegate permissions validation to API
        pass

    def _on_submit(self, event_data):
        approvers = event_data['required_approvers']
        self.pending_approvers.set(approvers)

    def _on_approve(self, event_data):
        approving_user = event_data['user']
        self.pending_approvers.remove(approving_user)
        if not self.pending_approvers.exists():
            self.accept()

    def _on_reject(self, event_data):
        self.pending_approvers.clear()
