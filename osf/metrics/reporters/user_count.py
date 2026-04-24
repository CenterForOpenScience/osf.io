from osf.models import OSFUser

from osf.metrics import UserSummaryReport
from ._base import DailyReporter
from osf.metrics.es8_metrics import UserSummaryReportEs8


class UserCountReporter(DailyReporter):

    def report(self, report_date):
        reports = []
        report_es8 = UserSummaryReportEs8(
            cycle_coverage=f"{report_date:%Y.%m.%d}",
            active=OSFUser.objects.filter(is_active=True, date_confirmed__date__lte=report_date).count(),
            deactivated=OSFUser.objects.filter(date_disabled__isnull=False, date_disabled__date__lte=report_date).count(),
            merged=OSFUser.objects.filter(date_registered__date__lte=report_date, merged_by__isnull=False).count(),
            new_users_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date).count(),
            new_users_with_institution_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date, institutionaffiliation__isnull=False).count(),
            unconfirmed=OSFUser.objects.filter(date_registered__date__lte=report_date, date_confirmed__isnull=True).count(),
        )
        reports.append(report_es8)
        report = UserSummaryReport(
            report_date=report_date,
            active=report_es8.active,
            deactivated=report_es8.deactivated,
            merged=report_es8.merged,
            new_users_daily=report_es8.new_users_daily,
            new_users_with_institution_daily=report_es8.new_users_with_institution_daily,
            unconfirmed=report_es8.unconfirmed,
        )
        reports.append(report)

        return reports
