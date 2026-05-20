import datetime

import elasticsearch8.dsl as esdsl
from elasticsearch_metrics import DAILY, YEARLY
import elasticsearch_metrics.imps.elastic8 as djelme

from osf.metrics.utils import cycle_coverage_date

__all__ = (
    'BaseDailyReport',
    'DailyDownloadCountReport',
    'DailyInstitutionSummaryReport',
    'DailyNewUserDomainReport',
    'DailyNodeSummaryReport',
    'DailyOsfstorageFileCountReport',
    'DailyPreprintSummaryReport',
    'DailyStorageAddonUsageReport',
    'DailyUserSummaryReport',
)


###
# base class

class BaseDailyReport(djelme.CyclicRecord):
    CYCLE_TIMEDEPTH = DAILY

    class Meta:
        abstract = True

    def __init__(self, *, report_date=None, **kwargs):
        super().__init__(**kwargs)
        # separate out report_date, so the property setter gets used
        if report_date is not None:
            self.report_date = report_date

    @property
    def report_date(self):
        _year, _month, _day = map(int, self.cycle_coverage.split('.'))
        return datetime.date(_year, _month, _day)

    @report_date.setter
    def report_date(self, d: str | datetime.date):
        self.cycle_coverage = cycle_coverage_date(
            datetime.date.fromisoformat(d) if isinstance(d, str) else d
        )


###
# reusable inner objects

class RunningTotal(esdsl.InnerDoc):
    total: int
    total_daily: int | None


class FileRunningTotals(esdsl.InnerDoc):
    total: int
    public: int
    private: int
    total_daily: int
    public_daily: int
    private_daily: int


class NodeRunningTotals(esdsl.InnerDoc):
    total: int
    total_excluding_spam: int | None
    public: int
    private: int
    total_daily: int
    total_daily_excluding_spam: int | None
    public_daily: int
    private_daily: int


class RegistrationRunningTotals(esdsl.InnerDoc):
    total: int
    public: int
    embargoed: int
    embargoed_v2: int
    withdrawn: int | None
    total_daily: int
    public_daily: int
    embargoed_daily: int
    embargoed_v2_daily: int
    withdrawn_daily: int | None


class UsageByStorageAddon(esdsl.InnerDoc):
    addon_shortname: str
    enabled_usersettings: RunningTotal
    linked_usersettings: RunningTotal
    deleted_usersettings: RunningTotal
    usersetting_links: RunningTotal
    connected_nodesettings: RunningTotal
    disconnected_nodesettings: RunningTotal
    deleted_nodesettings: RunningTotal


###
# daily reports

class DailyStorageAddonUsageReport(BaseDailyReport):
    usage_by_addon: list[UsageByStorageAddon]

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyDownloadCountReport(BaseDailyReport):
    daily_file_downloads: int

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyInstitutionSummaryReport(BaseDailyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'institution_id',)

    institution_id: str
    institution_name: str
    users: RunningTotal
    nodes: NodeRunningTotals
    projects: NodeRunningTotals
    registered_nodes: RegistrationRunningTotals
    registered_projects: RegistrationRunningTotals

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyNewUserDomainReport(BaseDailyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'domain_name',)

    domain_name: str
    new_user_count: int

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyNodeSummaryReport(BaseDailyReport):
    nodes: NodeRunningTotals
    projects: NodeRunningTotals
    registered_nodes: RegistrationRunningTotals
    registered_projects: RegistrationRunningTotals

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyOsfstorageFileCountReport(BaseDailyReport):
    files: FileRunningTotals

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyPreprintSummaryReport(BaseDailyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'provider_key',)
    provider_key: str
    preprint_count: int

    class Meta:
        timeseries_index_timedepth = YEARLY


class DailyUserSummaryReport(BaseDailyReport):
    active: int
    deactivated: int
    merged: int
    new_users_daily: int
    new_users_with_institution_daily: int
    unconfirmed: int

    class Meta:
        timeseries_index_timedepth = YEARLY
