from osf.models import OSFUser

from osf.metrics.reports import SpamSummaryReport
from ._base import MonthlyReporter
from osf.models import PreprintLog, NodeLog
from osf.models.spam import SpamStatus
from osf.metrics.es8_metrics import SpamSummaryReportEs8

class SpamCountReporter(MonthlyReporter):

    def report(self, **report_kwargs):
        assert not report_kwargs
        target_month = self.yearmonth.month_start()
        next_month = self.yearmonth.month_end()
        reports = []
        report_es8 = SpamSummaryReportEs8(
            cycle_coverage=f"{self.yearmonth:%Y.%m}",
            node_confirmed_spam=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_SPAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.node',
            ).count(),
            node_confirmed_ham=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_HAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.node',
            ).count(),
            node_flagged=NodeLog.objects.filter(
                action=NodeLog.FLAG_SPAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.node',
            ).count(),
            # Registration Log entries
            registration_confirmed_spam=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_SPAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.registration',
            ).count(),
            registration_confirmed_ham=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_HAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.registration',
            ).count(),
            registration_flagged=NodeLog.objects.filter(
                action=NodeLog.FLAG_SPAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.registration',
            ).count(),
            # Preprint Log entries
            preprint_confirmed_spam=PreprintLog.objects.filter(
                action=PreprintLog.CONFIRM_SPAM,
                created__gt=target_month,
                created__lt=next_month,
            ).count(),
            preprint_confirmed_ham=PreprintLog.objects.filter(
                action=PreprintLog.CONFIRM_HAM,
                created__gt=target_month,
                created__lt=next_month,
            ).count(),
            preprint_flagged=PreprintLog.objects.filter(
                action=PreprintLog.FLAG_SPAM,
                created__gt=target_month,
                created__lt=next_month,
            ).count(),
            # New Users marked as Spam/Ham
            user_marked_as_spam=OSFUser.objects.filter(
                spam_status=SpamStatus.SPAM,
                created__gt=target_month,
                created__lt=next_month,
            ).count(),
            user_marked_as_ham=OSFUser.objects.filter(
                spam_status=SpamStatus.HAM,
                created__gt=target_month,
                created__lt=next_month,
            ).count()
        )
        reports.append(report_es8)
        report = SpamSummaryReport(
            # Node Log entries
            node_confirmed_spam=report_es8.node_confirmed_spam,
            node_confirmed_ham=report_es8.node_confirmed_ham,
            node_flagged=report_es8.node_flagged,
            # Registration Log entries
            registration_confirmed_spam=report_es8.registration_confirmed_spam,
            registration_confirmed_ham=report_es8.registration_confirmed_ham,
            registration_flagged=report_es8.registration_flagged,
            # Preprint Log entries
            preprint_confirmed_spam=report_es8.preprint_confirmed_spam,
            preprint_confirmed_ham=report_es8.preprint_confirmed_ham,
            preprint_flagged=report_es8.preprint_flagged,
            # New Users marked as Spam/Ham
            user_marked_as_spam=report_es8.user_marked_as_spam,
            user_marked_as_ham=report_es8.user_marked_as_ham,
        )
        reports.append(report)
        return reports
