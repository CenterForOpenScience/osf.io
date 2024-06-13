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
from django.db.models import Subquery, OuterRef


class SpamCountReporter(MonthlyReporter):

    def report(self, report_yearmonth):
        target_month = report_yearmonth.target_month()
        next_month = report_yearmonth.next_month()

        node_flagged_reversed = Node.objects.filter(
            logs__id__in=Subquery(
                NodeLog.objects.filter(
                    node=OuterRef('id'),
                    action=NodeLog.FLAG_SPAM
                ).values('id')
            )
        ).filter(
            logs__id__in=Subquery(
                NodeLog.objects.filter(
                    node=OuterRef('id'),
                    created__gt=target_month,
                    created__lt=next_month,
                    action=NodeLog.CONFIRM_SPAM
                ).values('id')
            )
        )

        registration_flagged_reversed = Registration.objects.filter(
            logs__id__in=Subquery(
                NodeLog.objects.filter(
                    node=OuterRef('id'),
                    action=NodeLog.FLAG_SPAM
                ).values('id')
            )
        ).filter(
            logs__id__in=Subquery(
                NodeLog.objects.filter(
                    node=OuterRef('id'),
                    created__gt=target_month,
                    created__lt=next_month,
                    action=NodeLog.CONFIRM_SPAM
                ).values('id')
            )
        )

        preprint_flagged_reversed = Preprint.objects.filter(
            logs__id__in=Subquery(
                PreprintLog.objects.filter(
                    node=OuterRef('id'),
                    action=PreprintLog.FLAG_SPAM
                ).values('id')
            )
        ).filter(
            logs__id__in=Subquery(
                PreprintLog.objects.filter(
                    node=OuterRef('id'),
                    created__gt=target_month,
                    created__lt=next_month,
                    action=PreprintLog.CONFIRM_SPAM
                ).values('id')
            )
        )

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
            node_flagged_reversed=node_flagged_reversed.count(),
            node_flagged_reversed_akismet=node_flagged_reversed.filter(spam_data__who_flagged='akismet').count(),
            node_flagged_reversed_oopspam=node_flagged_reversed.filter(spam_data__who_flagged='oopspam').count(),
            node_flagged_reversed_both=node_flagged_reversed.filter(spam_data__who_flagged='both').count(),
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
            registration_flagged_reversed=registration_flagged_reversed.count(),
            registration_flagged_reversed_akismet=registration_flagged_reversed.filter(
                spam_data__who_flagged='akismet'
            ).count(),
            registration_flagged_reversed_oopspam=Registration.objects.filter(
                spam_data__who_flagged='oopspam'
            ).count(),
            registration_flagged_reversed_both=Registration.objects.filter(
                spam_data__who_flagged='both'
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
            preprint_flagged_reversed=preprint_flagged_reversed.count(),
            preprint_flagged_reversed_akismet=preprint_flagged_reversed.filter(
                spam_data__who_flagged='akismet'
            ).count(),
            preprint_flagged_reversed_oopspam=preprint_flagged_reversed.filter(
                spam_data__who_flagged='oopspam'
            ).count(),
            preprint_flagged_reversed_both=preprint_flagged_reversed.filter(
                spam_data__who_flagged='both'
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
