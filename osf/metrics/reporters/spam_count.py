from osf.models import OSFUser

from osf.metrics.reports import SpamSummaryReport
from ._base import MonthlyReporter
from osf.models import PreprintLog, NodeLog
from osf.models.spam import SpamStatus
from osf.external.oopspam.client import OOPSpamClient
from osf.external.askismet.client import AkismetClient


class SpamCountReporter(MonthlyReporter):

    def report(self, report_yearmonth):
        target_month = report_yearmonth.target_month()
        next_month = report_yearmonth.next_month()

        oopspam_client = OOPSpamClient()
        akismet_client = AkismetClient()

        oopspam_flagged = oopspam_client.get_flagged_count(target_month, next_month)
        oopspam_hammed = oopspam_client.get_hammed_count(target_month, next_month)

        akismet_flagged = akismet_client.get_flagged_count(target_month, next_month)
        akismet_hammed = akismet_client.get_hammed_count(target_month, next_month)

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
            oopspam_flagged=oopspam_flagged,
            oopspam_hammed=oopspam_hammed,
            akismet_flagged=akismet_flagged,
            akismet_hammed=akismet_hammed,
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

        return [report]
