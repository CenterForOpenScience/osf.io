import logging

from django.db.models import Q

from osf.metrics.reports import (
    InstitutionSummaryReport,
    RunningTotal,
    NodeRunningTotals,
    RegistrationRunningTotals,
)
from osf.models import Institution
from ._base import DailyReporter


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InstitutionSummaryReporter(DailyReporter):
    def report(self, date):
        institutions = Institution.objects.all()
        reports = []

        daily_query = Q(created__date=date)
        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        # `embargoed` used private status to determine embargoes, but old registrations could be private and unapproved registrations can also be private
        # `embargoed_v2` uses future embargo end dates on root
        embargo_v2_query = Q(root__embargo__end_date__date__gt=date)

        for institution in institutions:
            node_qs = institution.nodes.filter(
                deleted__isnull=True,
                created__date__lte=date,
            ).exclude(type="osf.registration")
            registration_qs = institution.nodes.filter(
                deleted__isnull=True,
                created__date__lte=date,
                type="osf.registration",
            )

            report = InstitutionSummaryReport(
                report_date=date,
                institution_id=institution._id,
                institution_name=institution.name,
                users=RunningTotal(
                    total=institution.get_institution_users()
                    .filter(is_active=True)
                    .count(),
                    total_daily=institution.get_institution_users()
                    .filter(date_confirmed__date=date)
                    .count(),
                ),
                nodes=NodeRunningTotals(
                    total=node_qs.count(),
                    public=node_qs.filter(public_query).count(),
                    private=node_qs.filter(private_query).count(),
                    total_daily=node_qs.filter(daily_query).count(),
                    public_daily=node_qs.filter(
                        public_query & daily_query
                    ).count(),
                    private_daily=node_qs.filter(
                        private_query & daily_query
                    ).count(),
                ),
                # Projects use get_roots to remove children
                projects=NodeRunningTotals(
                    total=node_qs.get_roots().count(),
                    public=node_qs.filter(public_query).get_roots().count(),
                    private=node_qs.filter(private_query).get_roots().count(),
                    total_daily=node_qs.filter(daily_query)
                    .get_roots()
                    .count(),
                    public_daily=node_qs.filter(public_query & daily_query)
                    .get_roots()
                    .count(),
                    private_daily=node_qs.filter(private_query & daily_query)
                    .get_roots()
                    .count(),
                ),
                registered_nodes=RegistrationRunningTotals(
                    total=registration_qs.count(),
                    public=registration_qs.filter(public_query).count(),
                    embargoed=registration_qs.filter(private_query).count(),
                    embargoed_v2=registration_qs.filter(
                        private_query & embargo_v2_query
                    ).count(),
                    total_daily=registration_qs.filter(daily_query).count(),
                    public_daily=registration_qs.filter(
                        public_query & daily_query
                    ).count(),
                    embargoed_daily=registration_qs.filter(
                        private_query & daily_query
                    ).count(),
                    embargoed_v2_daily=registration_qs.filter(
                        private_query & daily_query & embargo_v2_query
                    ).count(),
                ),
                registered_projects=RegistrationRunningTotals(
                    total=registration_qs.get_roots().count(),
                    public=registration_qs.filter(public_query)
                    .get_roots()
                    .count(),
                    embargoed=registration_qs.filter(private_query)
                    .get_roots()
                    .count(),
                    embargoed_v2=registration_qs.filter(
                        private_query & embargo_v2_query
                    )
                    .get_roots()
                    .count(),
                    total_daily=registration_qs.filter(daily_query)
                    .get_roots()
                    .count(),
                    public_daily=registration_qs.filter(
                        public_query & daily_query
                    )
                    .get_roots()
                    .count(),
                    embargoed_daily=registration_qs.filter(
                        private_query & daily_query
                    )
                    .get_roots()
                    .count(),
                    embargoed_v2_daily=registration_qs.filter(
                        private_query & daily_query & embargo_v2_query
                    )
                    .get_roots()
                    .count(),
                ),
            )

            reports.append(report)
        return reports

    def keen_events_from_report(self, report):
        event = {
            "institution": {
                "id": report.institution_id,
                "name": report.institution_name,
            },
            "users": report.users.to_dict(),
            "nodes": report.nodes.to_dict(),
            "projects": report.projects.to_dict(),
            "registered_nodes": report.registered_nodes.to_dict(),
            "registered_projects": report.registered_projects.to_dict(),
        }
        return {"institution_summary": [event]}
