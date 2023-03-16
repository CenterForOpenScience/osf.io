from osf.models import (
    OSFUser,
    Node,
    Registration,
    Preprint
)

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
            node_flagged_reversed=Node.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).distinct().count(),
            node_flagged_reversed_akismet=Node.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='akismet'
            ).distinct().count(),
            node_flagged_reversed_oopspam=Node.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='oopspam'
            ).distinct().count(),
            node_flagged_reversed_both=Node.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='both'
            ).distinct().count(),
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
            registration_flagged_reversed=Registration.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).distinct().count(),
            registration_flagged_reversed_akismet=Registration.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='akismet'
            ).distinct().count(),
            registration_flagged_reversed_oopspam=Registration.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='oopspam'
            ).distinct().count(),
            registration_flagged_reversed_both=Registration.objects.filter(
                logs__action=NodeLog.FLAG_SPAM
            ).filter(
                logs__action=NodeLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='both'
            ).distinct().count(),
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
            preprint_flagged_reversed=Preprint.objects.filter(
                logs__action=PreprintLog.FLAG_SPAM
            ).filter(
                logs__action=PreprintLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).distinct().count(),
            preprint_flagged_reversed_akismet=Preprint.objects.filter(
                logs__action=PreprintLog.FLAG_SPAM
            ).filter(
                logs__action=PreprintLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='akismet'
            ).distinct().count(),
            preprint_flagged_reversed_oopspam=Preprint.objects.filter(
                logs__action=PreprintLog.FLAG_SPAM
            ).filter(
                logs__action=PreprintLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='oopspam'
            ).distinct().count(),
            preprint_flagged_reversed_both=Preprint.objects.filter(
                logs__action=PreprintLog.FLAG_SPAM
            ).filter(
                logs__action=PreprintLog.CONFIRM_HAM,
                logs__created__gt=target_month,
                logs__created__lt=next_month,
            ).filter(
                spam_data__who_flagged='both'
            ).distinct().count(),
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

        return [report]
