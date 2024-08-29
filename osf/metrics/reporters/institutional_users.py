from django.contrib.contenttypes.models import ContentType

from osf import models as osfdb
from osf.metrics.reports import InstitutionalUserReport
from osf.metrics.utils import YearMonth
from website import settings as website_settings
from api.caching.utils import storage_usage_cache
from api.caching.tasks import update_storage_usage_cache
from api.caching.settings import STORAGE_USAGE_KEY
from ._base import MonthlyReporter


class InstitutionalUserReporter(MonthlyReporter):
    def report(self, yearmonth: YearMonth):
        before_datetime = yearmonth.next_month()
        institutions = osfdb.Institution.objects.all()

        for institution in institutions:
            users = institution.get_institution_users().filter(created__lt=before_datetime)
            for user in users.iterator():
                report = self.generate_report(institution, user, yearmonth, before_datetime)
                yield report

    def generate_report(self, institution, user, yearmonth, before_datetime):
        affiliation = user.get_institution_affiliation(institution._id)
        report = InstitutionalUserReport(
            report_yearmonth=yearmonth,
            institution_id=institution._id,
            user_id=user._id,
            department_name=affiliation.sso_department or None,
            month_last_login=user.date_last_login,
            account_creation_date=user.created.date(),
            orcid_id=user.get_verified_external_id('ORCID', verified_only=True),
            public_project_count=0,
            private_project_count=0,
            public_registration_count=0,
            embargoed_registration_count=0,
            storage_byte_count=0,
            public_file_count=0,
            published_preprint_count=0,
        )

        self.fill_counts(report, institution, user, before_datetime)
        return report

    def fill_counts(self, report, institution, user, before_datetime):
        nodes = self.get_user_nodes(institution, user, before_datetime)
        for node in nodes.iterator():
            self.update_node_counts(report, node, before_datetime)

        preprints = self.get_user_preprints(user, before_datetime)
        for preprint in preprints.iterator():
            self.update_preprint_counts(report, preprint)

    def get_user_nodes(self, institution, user, before_datetime):
        nodes = institution.nodes.filter(
            type__in=('osf.node', 'osf.registration'),
            created__lt=before_datetime,
            is_deleted=False,
        )
        return osfdb.Node.objects.get_nodes_for_user(user=user, base_queryset=nodes).select_related('embargo')

    def get_user_preprints(self, user, before_datetime):
        return osfdb.Preprint.objects.filter(
            _contributors=user,
            is_published=True,
            date_published__lt=before_datetime,
        )

    def update_node_counts(self, report, node, before_datetime):
        self.update_storage_usage(report, node)

        if node.is_public:
            report.public_file_count += self.get_file_count(node)

        if node.pk == node.root_id:
            if isinstance(node, osfdb.Node):
                if node.is_public:
                    report.public_project_count += 1
                else:
                    report.private_project_count += 1
            elif isinstance(node, osfdb.Registration):
                if node.is_public:
                    report.public_registration_count += 1
                elif node.embargo.end_date >= before_datetime:
                    report.embargoed_registration_count += 1

    def update_preprint_counts(self, report, preprint):
        if preprint.verified_publishable:
            report.published_preprint_count += 1
            report.public_file_count += self.get_file_count(preprint)
            self.update_storage_usage(report, preprint)

    def get_file_count(self, obj):
        return osfdb.OsfStorageFile.active.filter(
            target_object_id=obj.pk,
            target_content_type=ContentType.objects.get_for_model(osfdb.AbstractNode),
            created__lt=obj.created,
        ).count()

    def update_storage_usage(self, report, obj):
        if website_settings.ENABLE_STORAGE_USAGE_CACHE:
            cache_key = STORAGE_USAGE_KEY.format(target_id=obj._id)
            byte_count = storage_usage_cache.get(cache_key)
            if byte_count is None:
                update_storage_usage_cache(obj.id, obj._id)
                byte_count = storage_usage_cache.get(cache_key)

            if byte_count is not None:
                report.storage_byte_count += byte_count
