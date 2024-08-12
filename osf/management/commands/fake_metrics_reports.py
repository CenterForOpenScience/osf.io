from datetime import date, timedelta
from random import randint

from django.conf import settings
from django.core.management.base import BaseCommand

from osf.metrics import (
    UserSummaryReport,
    PreprintSummaryReport,
)
from osf.models import PreprintProvider


def fake_user_counts(days_back):
    yesterday = date.today() - timedelta(days=1)
    first_report = UserSummaryReport(
        report_date=(yesterday - timedelta(days=days_back)),
        active=randint(0, 23),
        deactivated=randint(0, 2),
        merged=randint(0, 4),
        new_users_daily=randint(0, 7),
        new_users_with_institution_daily=randint(0, 5),
        unconfirmed=randint(0, 3),
    )
    first_report.save()

    last_report = first_report
    while last_report.report_date < yesterday:
        new_user_count = randint(0, 500)
        new_report = UserSummaryReport(
            report_date=(last_report.report_date + timedelta(days=1)),
            active=(last_report.active + randint(0, new_user_count)),
            deactivated=(last_report.deactivated + randint(0, new_user_count)),
            merged=(last_report.merged + randint(0, new_user_count)),
            new_users_daily=new_user_count,
            new_users_with_institution_daily=randint(0, new_user_count),
            unconfirmed=(last_report.unconfirmed + randint(0, new_user_count)),
        )
        new_report.save()
        last_report = new_report


def fake_preprint_counts(days_back):
    yesterday = date.today() - timedelta(days=1)
    provider_keys = PreprintProvider.objects.all().values_list(
        "_id", flat=True
    )
    for day_delta in range(days_back):
        for provider_key in provider_keys:
            preprint_count = randint(100, 5000) * (days_back - day_delta)
            PreprintSummaryReport(
                report_date=yesterday - timedelta(days=day_delta),
                provider_key=provider_key,
                preprint_count=preprint_count,
            ).save()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise NotImplementedError("fake_reports requires DEBUG mode")
        fake_user_counts(1000)
        fake_preprint_counts(1000)
        # TODO: more reports
