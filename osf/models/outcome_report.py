from django.utils import timezone
from osf.utils.fields import NonNaiveDateTimeField
from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.sanctions import EmailApprovableSanction
from website.mails import mails

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.workflows import SanctionTypes, SanctionStates
from website import settings


class OutcomeReport(EmailApprovableSanction):
    SANCTION_TYPE = SanctionTypes.OUTCOME_REPORT
    DISPLAY_NAME = "Outcome Report"
    SHORT_NAME = "outcome_report"

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.TEST
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.TEST

    APPROVE_URL_TEMPLATE = settings.DOMAIN + "token_action/{node_id}/?token={token}"
    REJECT_URL_TEMPLATE = settings.DOMAIN + "token_action/{node_id}/?token={token}"

    _outcome_data = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    title = models.TextField(blank=True, default="", null=True)
    description = models.TextField(blank=True, default="", null=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    creator = models.ForeignKey(
        "OSFUser", related_name="schema_response", null=True, on_delete=models.CASCADE
    )
    schema = models.ForeignKey(
        "RegistrationSchema",
        related_name="schema_response",
        on_delete=models.CASCADE,
    )
    registration = models.OneToOneField(
        "Registration",
        related_name="outcome_report",
        on_delete=models.CASCADE,
    )

    @property
    def node(self):
        return self.registration.branched_from

    @property
    def is_public(self):
        return self.state == SanctionStates.APPROVED

    @property
    def outcome_data(self):
        return self._outcome_data

    @outcome_data.setter
    def outcome_data(self, data):
        self.schema.validate(data)
        self._outcome_data = data

    def delete(self, *args, **kwargs):
        self.deleted = timezone.now()

        if kwargs.get("save"):
            self.save()

    def add_log(self, action, params, auth):
        user = auth.user if auth else None
        log = OutcomeReportLog(action=action, user=user, params=params, report=self)
        log.save()
        return log

    def _get_registration(self):
        return self.registration

    def _notify_initiator(self):
        # Send email
        pass

    def _on_reject(self, event_data):
        # send rejection email
        self.add_log(OutcomeReportLog.REJECTED)
        self.delete(save=True)

    def _on_complete(self, event_data):
        super()._on_complete(event_data)
        # Indexing and archiving, send confirmation email
        self.add_log(OutcomeReportLog.APPROVED)

    class Meta:
        permissions = (
            ("read_outcome_report", "Can read the outcome report"),
            ("write_outcome_report", "Can edit the outcome report"),
            ("admin_outcome_report", "Can manage the outcome report"),
        )


class OutcomeReportLog(ObjectIDMixin, BaseModel):
    date = NonNaiveDateTimeField(default=timezone.now)
    action = models.CharField(max_length=255)
    report = models.ForeignKey(
        "OutcomeReport",
        related_name="logs",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        "OSFUser", db_index=True, null=True, blank=True, on_delete=models.CASCADE
    )
    params = DateTimeAwareJSONField(default=dict)

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
