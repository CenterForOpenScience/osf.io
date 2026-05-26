import collections.abc

import elasticsearch8.dsl as esdsl
from elasticsearch_metrics import MONTHLY, YEARLY
import elasticsearch_metrics.imps.elastic8 as djelme

from osf.metrics.fields import YearmonthField
from osf.metrics.utils import (
    YearMonth,
    cycle_coverage_yearmonth,
)

__all__ = (
    'BaseMonthlyReport',
    'MonthlyInstitutionSummaryReport',
    'MonthlyInstitutionalUserReport',
    'MonthlyPrivateSpamMetricsReport',
    'MonthlyPublicItemUsageReport',
    'MonthlySpamSummaryReport',
)


###
# base class

class BaseMonthlyReport(djelme.CyclicRecord):
    CYCLE_TIMEDEPTH = MONTHLY

    class Meta:
        abstract = True

    @classmethod
    def most_recent_cycle(cls, base_search=None) -> str | None:
        _search = base_search or cls.search()
        _search = _search[0:0]  # omit hits
        _search.aggs.bucket(
            'agg_most_recent_cycle',
            'terms',
            field='cycle_coverage',
            order={'_key': 'desc'},
            size=1,
        )
        _response = _search.execute()
        if not _response.aggregations:
            return None
        _buckets = _response.aggregations.agg_most_recent_cycle.buckets
        if not _buckets:
            return None
        return _buckets[0].key

    def __init__(self, *, report_yearmonth=None, **kwargs):
        super().__init__(**kwargs)
        # separate out report_yearmonth, so the property setter gets used
        if report_yearmonth is not None:
            self.report_yearmonth = report_yearmonth

    @property
    def report_yearmonth(self):
        _year, _month = map(int, self.cycle_coverage.split('.'))
        return YearMonth(_year, _month)

    @report_yearmonth.setter
    def report_yearmonth(self, ym):
        self.cycle_coverage = cycle_coverage_yearmonth(YearMonth.from_any(ym))


###
# monthly reports

class MonthlySpamSummaryReport(BaseMonthlyReport):
    node_confirmed_spam: int
    node_confirmed_ham: int
    node_flagged: int
    registration_confirmed_spam: int
    registration_confirmed_ham: int
    registration_flagged: int
    preprint_confirmed_spam: int
    preprint_confirmed_ham: int
    preprint_flagged: int
    user_marked_as_spam: int
    user_marked_as_ham: int

    class Meta:
        timeseries_index_timedepth = YEARLY


class MonthlyInstitutionalUserReport(BaseMonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'institution_id', 'user_id',)

    institution_id: str
    # user info:
    user_id: str
    user_name: str
    department_name: str | None
    month_last_login = YearmonthField()
    month_last_active = YearmonthField()
    account_creation_date = YearmonthField()
    orcid_id: str | None
    # counts:
    public_project_count: int
    private_project_count: int
    public_registration_count: int
    embargoed_registration_count: int
    published_preprint_count: int
    public_file_count: int = esdsl.mapped_field(esdsl.Long())
    storage_byte_count: int = esdsl.mapped_field(esdsl.Long())

    class Meta:
        timeseries_index_timedepth = YEARLY


class MonthlyInstitutionSummaryReport(BaseMonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'institution_id', )

    institution_id: str
    user_count: int
    public_project_count: int
    private_project_count: int
    public_registration_count: int
    embargoed_registration_count: int
    published_preprint_count: int
    storage_byte_count: int = esdsl.mapped_field(esdsl.Long())
    public_file_count: int = esdsl.mapped_field(esdsl.Long())
    monthly_logged_in_user_count: int = esdsl.mapped_field(esdsl.Long())
    monthly_active_user_count: int = esdsl.mapped_field(esdsl.Long())

    class Meta:
        timeseries_index_timedepth = YEARLY


class MonthlyPublicItemUsageReport(BaseMonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('cycle_coverage', 'item_iri')

    # where noted, fields are meant to correspond to defined terms from COUNTER
    # https://cop5.projectcounter.org/en/5.1/appendices/a-glossary-of-terms.html
    # https://coprd.countermetrics.org/en/1.0.1/appendices/a-glossary.html
    item_iri: str
    item_osfids: list[str]
    # fields built from aggregations -- more than one value unlikely, but possible
    item_types: list[str]     # counter:Data-Type
    platform_iris: list[str]  # counter:Platform
    database_iris: list[str]  # counter:Database
    provider_ids: list[str]   # osf-specific (usually corresponds to database_iri)

    # view counts include views on components or files contained by this item
    view_count: int | None = esdsl.mapped_field(esdsl.Long())
    view_session_count: int | None = esdsl.mapped_field(esdsl.Long())
    cumulative_view_count: int | None = esdsl.mapped_field(esdsl.Long())
    cumulative_view_session_count: int | None = esdsl.mapped_field(esdsl.Long())

    # download counts of this item only (not including contained components or files)
    download_count: int | None = esdsl.mapped_field(esdsl.Long())
    download_session_count: int | None = esdsl.mapped_field(esdsl.Long())
    cumulative_download_count: int | None = esdsl.mapped_field(esdsl.Long())
    cumulative_download_session_count: int | None = esdsl.mapped_field(esdsl.Long())

    class Meta:
        timeseries_index_timedepth = YEARLY

    @classmethod
    def from_last_month(
        cls,
        item_iris: collections.abc.Collection[str],
    ) -> list['MonthlyPublicItemUsageReport']:
        _last_month = YearMonth.from_today().prior()
        _from_last_month = list(cls.each_from_month(item_iris, _last_month))
        if item_iris and not _from_last_month:
            # monthly reporters may not run immediately at the beginning of the month,
            # but this could -- if none exist, try the month prior
            _from_last_month = list(cls.each_from_month(item_iris, _last_month.prior()))
        return _from_last_month

    @classmethod
    def each_from_month(
        cls,
        item_iris: collections.abc.Collection[str],
        yearmonth: YearMonth,
    ) -> collections.abc.Collection['MonthlyPublicItemUsageReport']:
        if item_iris:
            _search = (
                cls.search()
                .filter('term', cycle_coverage=cycle_coverage_yearmonth(yearmonth))
                .filter('terms', item_iri=item_iris)
                [:len(item_iris)]
            )
            yield from _search.execute()


class MonthlyPrivateSpamMetricsReport(BaseMonthlyReport):
    node_oopspam_flagged: int
    node_oopspam_hammed: int
    node_akismet_flagged: int
    node_akismet_hammed: int
    preprint_oopspam_flagged: int
    preprint_oopspam_hammed: int
    preprint_akismet_flagged: int
    preprint_akismet_hammed: int

    class Meta:
        timeseries_index_timedepth = YEARLY
