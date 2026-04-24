import logging

from django.db.models import Q

from osf.metrics.reports import (
    NodeSummaryReport,
    NodeRunningTotals,
    RegistrationRunningTotals,
)
from ._base import DailyReporter
from osf.metrics.es8_metrics import (
    NodeSummaryReportEs8,
    NodeRunningTotals as NodeRunningTotalsEs8,
    RegistrationRunningTotals as RegistrationRunningTotalsEs8
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NodeCountReporter(DailyReporter):

    def report(self, date):
        from osf.models import Node, Registration
        from osf.models.spam import SpamStatus

        node_qs = Node.objects.filter(deleted__isnull=True, created__date__lte=date)
        registration_qs = Registration.objects.filter(deleted__isnull=True, created__date__lte=date)

        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        created_today_query = Q(created__date=date)
        retracted_query = Q(retraction__isnull=False)
        retracted_today_query = Q(retraction__date_retracted__date=date)

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__date__gt=date)

        exclude_spam = ~Q(spam_status__in=[SpamStatus.SPAM, SpamStatus.FLAGGED])
        reports = []
        report_es8 = NodeSummaryReportEs8(
            cycle_coverage=f"{date:%Y.%m.%d}",
            # Nodes - the number of projects and components
            nodes=NodeRunningTotalsEs8(
                total=node_qs.count(),
                total_excluding_spam=node_qs.filter(exclude_spam).count(),
                public=node_qs.filter(public_query).count(),
                private=node_qs.filter(private_query).count(),
                total_daily=node_qs.filter(created_today_query).count(),
                total_daily_excluding_spam=node_qs.filter(created_today_query).filter(exclude_spam).count(),
                public_daily=node_qs.filter(public_query & created_today_query).count(),
                private_daily=node_qs.filter(private_query & created_today_query).count(),
            ),
            # Projects - the number of top-level only projects
            projects=NodeRunningTotalsEs8(
                total=node_qs.get_roots().count(),
                total_excluding_spam=node_qs.get_roots().filter(exclude_spam).count(),
                public=node_qs.filter(public_query).get_roots().count(),
                private=node_qs.filter(private_query).get_roots().count(),
                total_daily=node_qs.filter(created_today_query).get_roots().count(),
                total_daily_excluding_spam=node_qs.filter(created_today_query).get_roots().filter(exclude_spam).count(),
                public_daily=node_qs.filter(public_query & created_today_query).get_roots().count(),
                private_daily=node_qs.filter(private_query & created_today_query).get_roots().count(),
            ),
            # Registered Nodes - the number of registered projects and components
            registered_nodes=RegistrationRunningTotalsEs8(
                total=registration_qs.count(),
                public=registration_qs.filter(public_query).count(),
                embargoed=registration_qs.filter(private_query).count(),
                embargoed_v2=registration_qs.filter(private_query & embargo_v2_query).count(),
                withdrawn=registration_qs.filter(retracted_query).count(),
                total_daily=registration_qs.filter(created_today_query).count(),
                public_daily=registration_qs.filter(public_query & created_today_query).count(),
                embargoed_daily=registration_qs.filter(private_query & created_today_query).count(),
                embargoed_v2_daily=registration_qs.filter(private_query & created_today_query & embargo_v2_query).count(),
                withdrawn_daily=registration_qs.filter(retracted_query & retracted_today_query).count(),

            ),
            # Registered Projects - the number of registered top level projects
            registered_projects=RegistrationRunningTotalsEs8(
                total=registration_qs.get_roots().count(),
                public=registration_qs.filter(public_query).get_roots().count(),
                embargoed=registration_qs.filter(private_query).get_roots().count(),
                embargoed_v2=registration_qs.filter(private_query & embargo_v2_query).get_roots().count(),
                withdrawn=registration_qs.filter(retracted_query).get_roots().count(),
                total_daily=registration_qs.filter(created_today_query).get_roots().count(),
                public_daily=registration_qs.filter(public_query & created_today_query).get_roots().count(),
                embargoed_daily=registration_qs.filter(private_query & created_today_query).get_roots().count(),
                embargoed_v2_daily=registration_qs.filter(private_query & created_today_query & embargo_v2_query).get_roots().count(),
                withdrawn_daily=registration_qs.filter(retracted_query & retracted_today_query).get_roots().count(),
            ),
        )
        reports.append(report_es8)
        report = NodeSummaryReport(
            report_date=date,
            # Nodes - the number of projects and components
            nodes=NodeRunningTotals(
                total=report_es8.nodes.total,
                total_excluding_spam=report_es8.nodes.total_excluding_spam,
                public=report_es8.nodes.public,
                private=report_es8.nodes.private,
                total_daily=report_es8.nodes.total_daily,
                total_daily_excluding_spam=report_es8.nodes.total_daily_excluding_spam,
                public_daily=report_es8.nodes.public_daily,
                private_daily=report_es8.nodes.private_daily,
            ),
            # Projects - the number of top-level only projects
            projects=NodeRunningTotals(
                total=report_es8.projects.total,
                total_excluding_spam=report_es8.projects.total_excluding_spam,
                public=report_es8.projects.public,
                private=report_es8.projects.private,
                total_daily=report_es8.projects.total_daily,
                total_daily_excluding_spam=report_es8.projects.total_daily_excluding_spam,
                public_daily=report_es8.projects.public_daily,
                private_daily=report_es8.projects.private_daily,
            ),
            # Registered Nodes - the number of registered projects and components
            registered_nodes=RegistrationRunningTotals(
                total=report_es8.registered_nodes.total,
                public=report_es8.registered_nodes.public,
                embargoed=report_es8.registered_nodes.embargoed,
                embargoed_v2=report_es8.registered_nodes.embargoed_v2,
                withdrawn=report_es8.registered_nodes.withdrawn,
                total_daily=report_es8.registered_nodes.total_daily,
                public_daily=report_es8.registered_nodes.public_daily,
                embargoed_daily=report_es8.registered_nodes.embargoed_daily,
                embargoed_v2_daily=report_es8.registered_nodes.embargoed_v2_daily,
                withdrawn_daily=report_es8.registered_nodes.withdrawn_daily,
            ),
            # Registered Projects - the number of registered top level projects
            registered_projects=RegistrationRunningTotals(
                total=report_es8.registered_projects.total,
                public=report_es8.registered_projects.public,
                embargoed=report_es8.registered_projects.embargoed,
                embargoed_v2=report_es8.registered_projects.embargoed_v2,
                withdrawn=report_es8.registered_projects.withdrawn,
                total_daily=report_es8.registered_projects.total_daily,
                public_daily=report_es8.registered_projects.public_daily,
                embargoed_daily=report_es8.registered_projects.embargoed_daily,
                embargoed_v2_daily=report_es8.registered_projects.embargoed_v2_daily,
                withdrawn_daily=report_es8.registered_projects.withdrawn_daily,
            ),
        )
        reports.append(report)

        return reports
