from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, F, Sum

from osf.models import Institution, Preprint, AbstractNode, FileVersion
from osf.models.spam import SpamStatus
from addons.osfstorage.models import OsfStorageFile
from osf.metrics.reports import InstitutionMonthlySummaryReport
from osf.metrics.utils import YearMonth
from ._base import MonthlyReporter
from datetime import datetime


class InstitutionalSummaryMonthlyReporter(MonthlyReporter):
    """Generate an InstitutionMonthlySummaryReport for each institution."""

    def report(self, yearmonth: YearMonth):
        for institution in Institution.objects.all():
            yield self.generate_report(institution, yearmonth)

    def generate_report(self, institution, yearmonth):
        node_queryset = institution.nodes.filter(deleted__isnull=True)

        return InstitutionMonthlySummaryReport(
            institution_id=institution._id,
            user_count=institution.get_institution_users().count(),
            private_project_count=self._get_count(node_queryset, 'osf.node', is_public=False),
            public_project_count=self._get_count(node_queryset, 'osf.node', is_public=True),
            public_registration_count=self._get_count(node_queryset, 'osf.registration', is_public=True),
            embargoed_registration_count=self._get_count(node_queryset, 'osf.registration', is_public=False),
            published_preprint_count=self.get_published_preprints(institution).count(),
            storage_byte_count=self.get_storage_size(node_queryset, institution),
            public_file_count=self.get_files(node_queryset, institution, is_public=True).count(),
            monthly_logged_in_user_count=self.get_monthly_logged_in_user_count(institution, yearmonth),
            monthly_active_user_count=self.get_monthly_active_user_count(institution, yearmonth),
        )

    def _get_count(self, node_queryset, node_type, is_public):
        return node_queryset.filter(type=node_type, is_public=is_public, root_id=F('pk')).count()

    def get_published_preprints(self, institution):
        return Preprint.objects.can_view().filter(
            affiliated_institutions=institution
        ).exclude(spam_status=SpamStatus.SPAM)

    def get_files(self, node_queryset, institution, is_public=None):
        public_kwargs = {}
        if is_public:
            public_kwargs = {'is_public': is_public}

        target_node_q = Q(
            target_object_id__in=node_queryset.filter(**public_kwargs).values('pk'),
            target_content_type=ContentType.objects.get_for_model(AbstractNode),
        )
        target_preprint_q = Q(
            target_object_id__in=self.get_published_preprints(institution).values('pk'),
            target_content_type=ContentType.objects.get_for_model(Preprint),
        )
        return OsfStorageFile.objects.filter(
            deleted__isnull=True, purged__isnull=True
        ).filter(target_node_q | target_preprint_q)

    def get_storage_size(self, node_queryset, institution):
        files = self.get_files(node_queryset, institution)
        return FileVersion.objects.filter(
            size__gt=0,
            purged__isnull=True,
            basefilenode__in=files
        ).aggregate(storage_bytes=Sum('size', default=0))['storage_bytes']

    def get_month_start_end(self, yearmonth):
        # Get the first day of the month
        start_date = datetime(yearmonth.year, yearmonth.month, 1)
        # Calculate the first day of the next month
        if yearmonth.month == 12:
            end_date = datetime(yearmonth.year + 1, 1, 1)
        else:
            end_date = datetime(yearmonth.year, yearmonth.month + 1, 1)
        return start_date, end_date

    def get_monthly_logged_in_user_count(self, institution, yearmonth):
        start_date, end_date = self.get_month_start_end(yearmonth)
        return institution.get_institution_users().filter(
            date_last_login__gte=start_date,
            date_last_login__lt=end_date
        ).count()

    def get_monthly_active_user_count(self, institution, yearmonth):
        start_date, end_date = self.get_month_start_end(yearmonth)
        return institution.get_institution_users().filter(
            date_disabled__isnull=True,
            date_last_login__gte=start_date,
            date_last_login__lt=end_date
        ).count()
