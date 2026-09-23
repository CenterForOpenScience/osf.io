import re
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone

from osf.utils.fields import NonNaiveDateTimeField

MAX_REPORT_RECIPIENTS = 3


class StuckRegistrationReportCadence(models.TextChoices):
    INSTANT = 'instantly', 'Instant'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'


REPORT_INTERVALS = {
    StuckRegistrationReportCadence.INSTANT: timedelta(0),
    StuckRegistrationReportCadence.DAILY: timedelta(hours=23),
    StuckRegistrationReportCadence.WEEKLY: timedelta(days=6, hours=23),
}


class StuckRegistrationReportConfig(models.Model):
    emails = ArrayField(models.EmailField(), default=list, blank=True)
    cadence = models.CharField(max_length=32, choices=StuckRegistrationReportCadence.choices, default=StuckRegistrationReportCadence.DAILY)
    last_sent = NonNaiveDateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.first() or cls.objects.create()

    @staticmethod
    def parse_recipients(raw):
        """
        convert an admin-entered string into email addresses, raising ValidationError on a typo
        """
        addresses = [address for address in re.split(r'[,;\s]+', raw or '') if address]
        if len(addresses) > MAX_REPORT_RECIPIENTS:
            raise ValidationError(
                f'At most {MAX_REPORT_RECIPIENTS} addresses may receive the report, got {len(addresses)}.'
            )
        validator = EmailValidator()
        for address in addresses:
            validator(address)
        return addresses

    def report_is_due(self, now=None):
        if not self.emails:
            return False
        if self.last_sent is None:
            return True
        return (now or timezone.now()) - self.last_sent >= REPORT_INTERVALS[self.cadence]
