import dataclasses
import datetime

from django.contrib.contenttypes.models import ContentType

from osf import models as osfdb
from addons.osfstorage.models import OsfStorageFile
from api.caching.settings import STORAGE_USAGE_KEY
from api.caching.utils import storage_usage_cache
from api.caching.tasks import update_storage_usage_cache
from osf.metrics.reports import InstitutionalUserReport
from osf.metrics.utils import YearMonth
from website import settings as website_settings
from ._base import MonthlyReporter


_CHUNK_SIZE = 500


class InstitutionalUsersReporter(MonthlyReporter):
    def report(self, yearmonth: YearMonth):
        _before_datetime = yearmonth.next_month()
        for _institution in osfdb.Institution.objects.all():
            _user_qs = _institution.get_institution_users().filter(created__lt=_before_datetime)
            for _user in _user_qs.iterator(chunk_size=_CHUNK_SIZE):
                _helper = _InstiUserReportHelper(_institution, _user, yearmonth, _before_datetime)
                yield _helper.report


# helper
@dataclasses.dataclass
class _InstiUserReportHelper:
    institution: osfdb.Institution
    user: osfdb.OSFUser
    yearmonth: YearMonth
    before_datetime: datetime.datetime
    report: InstitutionalUserReport = dataclasses.field(init=False)

    def __post_init__(self):
        _affiliation = self.user.get_institution_affiliation(self.institution._id)
        self.report = InstitutionalUserReport(
            report_yearmonth=self.yearmonth,
            institution_id=self.institution._id,
            user_id=self.user._id,
            department_name=(_affiliation.sso_department or None),
            month_last_login=YearMonth.from_date(self.user.date_last_login),
            account_creation_date=YearMonth.from_date(self.user.created),
            orcid_id=self.user.get_verified_external_id('ORCID', verified_only=True),
            # initialize counts to 0:
            public_project_count=0,
            private_project_count=0,
            public_registration_count=0,
            embargoed_registration_count=0,
            storage_byte_count=0,
            public_file_count=0,
            published_preprint_count=0,
        )
        self._fill_counts()

    def _fill_counts(self) -> None:
        for _preprint in self._preprint_queryset().iterator(chunk_size=_CHUNK_SIZE):
            self._add_counts_for_preprint(_preprint)
        for _node in self._node_queryset().iterator(chunk_size=_CHUNK_SIZE):
            _is_root = (_node.pk == _node.root_id)
            if not _is_root:
                self._add_counts_for_component(_node)
            elif isinstance(_node, osfdb.Node):
                self._add_counts_for_project(_node)
            elif isinstance(_node, osfdb.Registration):
                self._add_counts_for_registration(_node)
            else:
                raise ValueError(f'expected "node" to be project, component, or registration; got {_node} (type {type(_node)})')

    def _node_queryset(self):
        _institution_node_qs = self.institution.nodes.filter(
            type__in=('osf.node', 'osf.registration'),  # `type` field from TypedModel
            created__lt=self.before_datetime,
            is_deleted=False,
        )
        _user_institution_node_qs = osfdb.Node.objects.get_nodes_for_user(
            user=self.user,
            base_queryset=_institution_node_qs,
        )
        return _user_institution_node_qs.select_related('embargo')

    def _preprint_queryset(self):
        if not hasattr(osfdb.Preprint, 'affiliated_institutions'):
            return osfdb.Preprint.objects.none()  # HACK: preprints affiliation project still in-progress
        return self.institution.preprints.filter(
            _contributors=self.user,
            is_published=True,
            date_published__lt=self.before_datetime,
        )

    def _add_counts_for_project(self, project: osfdb.Node) -> None:
        self._add_storage_usage(project)
        if project.is_public:
            self.report.public_project_count += 1
            self._add_public_file_count(project)
        else:
            self.report.private_project_count += 1

    def _add_counts_for_registration(self, reg: osfdb.Registration) -> None:
        self._add_storage_usage(reg)
        if reg.embargo and (reg.embargo.end_date >= self.before_datetime):
            self.report.embargoed_registration_count += 1
        elif reg.is_public:
            self.report.public_registration_count += 1
            self._add_public_file_count(reg)

    def _add_counts_for_component(self, component: osfdb.AbstractNode) -> None:
        self._add_storage_usage(component)
        if component.is_public:
            self._add_public_file_count(component)

    def _add_counts_for_preprint(self, preprint: osfdb.Preprint) -> None:
        if preprint.verified_publishable:
            self.report.published_preprint_count += 1
            self._add_storage_usage(preprint)
            self._add_public_file_count(preprint)

    def _add_public_file_count(self, filetarget: osfdb.AbstractNode | osfdb.Preprint) -> None:
        _file_queryset = OsfStorageFile.active.filter(
            target_object_id=filetarget.pk,
            target_content_type=ContentType.objects.get_for_model(filetarget),
            created__lt=self.before_datetime,
        )
        self.report.public_file_count += _file_queryset.count()

    def _add_storage_usage(self, obj: osfdb.AbstractNode | osfdb.Preprint) -> None:
        if website_settings.ENABLE_STORAGE_USAGE_CACHE:
            _cache_key = STORAGE_USAGE_KEY.format(target_id=obj._id)
            _byte_count = storage_usage_cache.get(_cache_key)
            if _byte_count is None:
                update_storage_usage_cache(obj.id, obj._id)
                _byte_count = storage_usage_cache.get(_cache_key)
            if _byte_count is not None:
                self.report.storage_byte_count += _byte_count
