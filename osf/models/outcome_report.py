from django.utils import timezone
from osf.utils.fields import NonNaiveDateTimeField
from django.db import models

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.models.base import GuidMixin, BaseModel


class OutcomeReport(GuidMixin, BaseModel):
    _responses = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    public =  NonNaiveDateTimeField(null=True, blank=True)
    schema = models.ForeignKey(
        "RegistrationSchema",
        related_name="outcome_reports",
        on_delete=models.CASCADE,
    )
    node = models.ForeignKey(
        "AbstractNode",
        related_name="outcome_reports",
        on_delete=models.CASCADE,
    )

    @property
    def responses(self):
        return self._responses

    @responses.setter
    def responses(self, data):
        self.schema.validate_metadata(data)
        self.responses = data

    @property
    def is_public(self):
        return bool(self.public)

    @is_public.setter
    def is_public(self, value):
        if value is True:
            self.public = timezone.now()
        else:
            self.public = None

        self.save()

    def delete(self, *args, **kwargs):
        self.deleted = timezone.now()

        if kwargs.get("save"):
            self.save()

    @property
    def versions(self):
        outcome_report = OutcomeReport.objects.get(guids___id=self._id)
        return OutcomeReport.objects.filter(
            deleted__isnull=True,
            public__isnull=False,
            node=outcome_report.node,
            schema=outcome_report.schema
        )

