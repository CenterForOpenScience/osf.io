from osf.models import OSFUser

from osf.metrics.daily_reports import DailyUserSummaryReport
from osf.metrics.utils import cycle_coverage_date
from ._base import DailyReporter


class UserCountReporter(DailyReporter):

    def report(self, report_date):
        yield DailyUserSummaryReport(
            cycle_coverage=cycle_coverage_date(report_date),
            active=OSFUser.objects.filter(is_active=True, date_confirmed__date__lte=report_date).count(),
            deactivated=OSFUser.objects.filter(date_disabled__isnull=False, date_disabled__date__lte=report_date).count(),
            merged=OSFUser.objects.filter(date_registered__date__lte=report_date, merged_by__isnull=False).count(),
            new_users_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date).count(),
            new_users_with_institution_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date, institutionaffiliation__isnull=False).count(),
            unconfirmed=OSFUser.objects.filter(date_registered__date__lte=report_date, date_confirmed__isnull=True).count(),
        )
