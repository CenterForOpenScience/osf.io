from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, F, Sum, Count

from osf.models import Institution, Preprint, AbstractNode, FileVersion
from osf.models.spam import SpamStatus
from addons.osfstorage.models import OsfStorageFile
from osf.metrics.reports import (
    InstitutionMonthlySummaryReport,
    License as ReporterLicense,
    Addon as ReporterAddon,
    StorageRegion as ReporterStorageRegion,
    Department as ReporterDepartment,
)
from osf.metrics.utils import YearMonth
from ._base import MonthlyReporter
from website import settings


class InstitutionalSummaryMonthlyReporter(MonthlyReporter):
    """Generate an InstitutionMonthlySummaryReport for each institution."""

    def report(self, yearmonth: YearMonth):
        for institution in Institution.objects.all():
            yield self.generate_report(institution, yearmonth)

    def generate_report(self, institution, yearmonth):
        node_queryset = institution.nodes.filter(deleted__isnull=True)

        return InstitutionMonthlySummaryReport(
            institution_id=institution._id,
            public_project_count=self._get_count(node_queryset, 'osf.node', is_public=True),
            private_project_count=self._get_count(node_queryset, 'osf.node', is_public=False),
            public_registration_count=self._get_count(node_queryset, 'osf.registration', is_public=True),
            embargoed_registration_count=self._get_count(node_queryset, 'osf.registration', is_public=False),
            published_preprint_count=self.get_published_preprints(institution).count(),
            public_file_count=self.get_files(node_queryset, institution, is_public=True).count(),
            private_file_count=self.get_files(node_queryset, institution, is_public=False).count(),
            public_storage_count=self.get_storage_size(node_queryset, institution, is_public=True),
            private_storage_count=self.get_storage_size(node_queryset, institution, is_public=False),
            departments=self.get_department_count(institution),
            licenses=self.get_license_count(node_queryset),
            addons=self.get_addons_count(),
            storage_regions=self.get_storage_region_count(node_queryset),
        )

    def _get_count(self, node_queryset, node_type, is_public):
        return node_queryset.filter(type=node_type, is_public=is_public, root_id=F('pk')).count()

    def get_published_preprints(self, institution):
        if not hasattr(Preprint, "affiliated_institutions"):
            return Preprint.objects.none()
        return Preprint.objects.can_view().filter(
            affiliated_institutions=institution
        ).exclude(spam_status=SpamStatus.SPAM)

    def get_files(self, node_queryset, institution, is_public):
        target_node_q = Q(
            target_object_id__in=node_queryset.filter(is_public=is_public).values("pk"),
            target_content_type=ContentType.objects.get_for_model(AbstractNode),
        )
        target_preprint_q = Q(
            target_object_id__in=self.get_published_preprints(institution).values("pk"),
            target_content_type=ContentType.objects.get_for_model(Preprint),
        )
        return OsfStorageFile.objects.filter(
            deleted__isnull=True, purged__isnull=True
        ).filter(target_node_q | target_preprint_q)

    def get_storage_size(self, node_queryset, institution, is_public):
        files = self.get_files(node_queryset, institution, is_public)
        return FileVersion.objects.filter(
            size__gt=0, purged__isnull=True, basefilenode__in=files
        ).aggregate(storage_bytes=Sum("size", default=0))["storage_bytes"]

    def get_license_count(self, node_queryset):
        licenses = node_queryset.exclude(node_license=None).values(
            "node_license__node_license__name", "node_license___id"
        ).annotate(total=Count("node_license"))

        license_list = [
            ReporterLicense(
                id=license_data["node_license___id"],
                name=license_data["node_license__node_license__name"],
                total=license_data["total"],
            )
            for license_data in licenses
        ]

        license_list.append(
            ReporterLicense(
                id=None,
                name="Default (No license selected)",
                total=node_queryset.filter(node_license=None).count(),
            )
        )

        return license_list

    def get_addons_count(self):
        storage_addons = [
            addon for addon in settings.ADDONS_AVAILABLE if "storage" in addon.categories
        ]

        addon_counts = []
        for addon in storage_addons:
            node_settings = addon.get_model("NodeSettings").objects.exclude(
                owner__isnull=True,
                owner__deleted__isnull=False,
                owner__spam_status=SpamStatus.SPAM,
            )
            is_oauth = hasattr(addon.get_model("NodeSettings"), "external_account")
            filter_condition = Q(external_account__isnull=False) if is_oauth else Q()
            count = node_settings.filter(filter_condition).count()
            addon_counts.append(ReporterAddon(name=addon.short_name, total=count))

        return addon_counts

    def get_storage_region_count(self, node_queryset):
        region_counts = node_queryset.values(
            "addons_osfstorage_node_settings__region___id",
            "addons_osfstorage_node_settings__region__name",
        ).annotate(total=Count("addons_osfstorage_node_settings__region___id"))

        return [
            ReporterStorageRegion(
                id=region["addons_osfstorage_node_settings__region___id"],
                name=region["addons_osfstorage_node_settings__region__name"],
                total=region["total"],
            )
            for region in region_counts
        ]

    def get_department_count(self, institution):
        departments = institution.institutionaffiliation_set.exclude(
            sso_department__isnull=True
        ).values("sso_department").annotate(total=Count("sso_department"))

        return [
            ReporterDepartment(name=dept["sso_department"], total=dept["total"])
            for dept in departments
        ]
