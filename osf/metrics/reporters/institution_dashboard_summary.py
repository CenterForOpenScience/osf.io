import logging

from django.db.models import Q

from osf.metrics.reports import (
    InstitutionDashboardSummaryReport,
    RunningTotal,
    NodeRunningTotals,
    RegistrationRunningTotals,
    FileRunningTotals,
    DataRunningTotals
)
from osf.models import Institution
from ._base import DailyReporter


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InstitutionDashboardSummaryReporter(DailyReporter):
    def report(self, date):
        institutions = Institution.objects.all()
        reports = []

        daily_query = Q(created__date=date)
        public_query = Q(is_public=True)
        private_query = Q(is_public=False)

        embargo_v2_query = Q(root__embargo__end_date__date__gt=date)

        for institution in institutions:
            node_qs = institution.nodes.filter(
                deleted__isnull=True,
                created__date__lte=date,
            ).exclude(type='osf.registration')
            registration_qs = institution.nodes.filter(
                deleted__isnull=True,
                created__date__lte=date,
                type='osf.registration',
            )

            report = InstitutionDashboardSummaryReport(
                report_date=date,
                institution_id=institution._id,
                institution_name=institution.name,
                users=RunningTotal(
                    total=institution.get_institution_users().filter(is_active=True).count(),
                    total_daily=institution.get_institution_users().filter(date_confirmed__date=date).count(),
                ),
                # Projects use get_roots to remove children
                projects=NodeRunningTotals(
                    total=node_qs.get_roots().count(),
                    public=node_qs.filter(public_query).get_roots().count(),
                    private=node_qs.filter(private_query).get_roots().count(),

                    total_daily=node_qs.filter(daily_query).get_roots().count(),
                    public_daily=node_qs.filter(public_query & daily_query).get_roots().count(),
                    private_daily=node_qs.filter(private_query & daily_query).get_roots().count(),
                ),
                registerations=RegistrationRunningTotals(
                    total=registration_qs.count(),
                    public=registration_qs.filter(public_query).count(),
                    embargoed=registration_qs.filter(private_query).count(),
                    embargoed_v2=registration_qs.filter(private_query & embargo_v2_query).count(),

                    total_daily=registration_qs.filter(daily_query).count(),
                    public_daily=registration_qs.filter(public_query & daily_query).count(),
                    embargoed_daily=registration_qs.filter(private_query & daily_query).count(),
                    embargoed_v2_daily=registration_qs.filter(private_query & daily_query & embargo_v2_query).count(),
                ),
                files=FileRunningTotals(),
                data=DataRunningTotals(),
            )

            reports.append(report)
        return reports