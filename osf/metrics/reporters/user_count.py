from osf.models import OSFUser

from osf.metrics import UserSummaryReport
from ._base import DailyReporter


class UserCountReporter(DailyReporter):

    def report(self, report_date):
        report = UserSummaryReport(
            report_date=report_date,
            active=OSFUser.objects.filter(is_active=True, date_confirmed__date__lte=report_date).count(),
            deactivated=OSFUser.objects.filter(date_disabled__isnull=False, date_disabled__date__lte=report_date).count(),
            merged=OSFUser.objects.filter(date_registered__date__lte=report_date, merged_by__isnull=False).count(),
            new_users_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date).count(),
            new_users_with_institution_daily=OSFUser.objects.filter(is_active=True, date_confirmed__date=report_date, institutionaffiliation__isnull=False).count(),
            unconfirmed=OSFUser.objects.filter(date_registered__date__lte=report_date, date_confirmed__isnull=True).count(),
        )

        return [report]

    def keen_events_from_report(self, report):
        event = {
            'status': {
                'active': report.active,
                'deactivated': report.deactivated,
                'merged': report.merged,
                'new_users_daily': report.new_users_daily,
                'new_users_with_institution_daily': report.new_users_with_institution_daily,
                'unconfirmed': report.unconfirmed,
            }
        }
        return {'user_summary': [event]}
