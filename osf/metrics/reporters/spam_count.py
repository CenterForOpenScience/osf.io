from osf.models import OSFUser

from osf.metrics.reports import SpamSummaryReport
from ._base import MonthlyReporter
from osf.models import PreprintLog, NodeLog
from osf.models.spam import SpamStatus


class SpamCountReporter(MonthlyReporter):

    def report(self, report_yearmonth):
        target_month = report_yearmonth.target_month()
        next_month = report_yearmonth.next_month()

        report = SpamSummaryReport(
            report_yearmonth=str(report_yearmonth),
            # Node Log entries
            confirmed_spam_node=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_SPAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.node',
            ).count(),
            nodes_confirmed_ham=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_HAM,
                created__gt=target_month,
                created__lt=next_month,
                node__type='osf.node',
            ).count(),
            nodes_flagged=NodeLog.objects.filter(
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
            users_marked_as_spam=OSFUser.objects.filter(
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

        return [report]
