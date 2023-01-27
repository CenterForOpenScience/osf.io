from osf.models import OSFUser

from osf.metrics.reports import SpamReport
from ._base import MonthlyReporter
from osf.models import PreprintLog, NodeLog
from osf.models.spam import SpamStatus

import dateutil
from django.utils import timezone


class SpamCountReporter(MonthlyReporter):

    def report(self, report_date):
        today = timezone.now()
        last_month = (today - dateutil.relativedelta.relativedelta(months=1))

        report = SpamReport(
            report_date=report_date,
            # Node Log entries
            confirmed_spam_node=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_SPAM,
                created__gt=last_month,
                node__type='osf.node',
            ).count(),
            nodes_confirmed_ham=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_HAM,
                created__gt=last_month,
                node__type='osf.node',
            ).count(),
            nodes_flagged=NodeLog.objects.filter(
                action=NodeLog.FLAG_SPAM,
                created__gt=last_month,
                node__type='osf.node',
            ).count(),
            # Registration Log entries
            registration_confirmed_spam=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_SPAM,
                created__gt=last_month,
                node__type='osf.registration',
            ).count(),
            registration_confirmed_ham=NodeLog.objects.filter(
                action=NodeLog.CONFIRM_HAM,
                created__gt=last_month,
                node__type='osf.registration',
            ).count(),
            registration_flagged=NodeLog.objects.filter(
                action=NodeLog.FLAG_SPAM,
                created__gt=last_month,
                node__type='osf.registration',
            ).count(),
            # Preprint Log entries
            preprint_confirmed_spam=PreprintLog.objects.filter(
                action=PreprintLog.CONFIRM_SPAM,
                created__gt=last_month,
            ).count(),
            preprint_confirmed_ham=PreprintLog.objects.filter(
                action=PreprintLog.CONFIRM_HAM,
                created__gt=last_month,
            ).count(),
            preprint_flagged=PreprintLog.objects.filter(
                action=PreprintLog.FLAG_SPAM,
                created__gt=last_month,
            ).count(),
            # New Users marked as Spam/Ham
            users_marked_as_spam=OSFUser.objects.filter(
                spam_status=SpamStatus.SPAM,
                created__gt=last_month
            ).count(),
            user_marked_as_ham=OSFUser.objects.filter(
                spam_status=SpamStatus.HAM,
                created__gt=last_month
            ).count()
        )

        return [report]
