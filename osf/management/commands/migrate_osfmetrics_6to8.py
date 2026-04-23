import collections
import datetime
import functools
import logging
import uuid

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import OperationalError as DjangoOperationalError
from elasticsearch6.exceptions import ConnectionError as Elastic6ConnectionError
from elasticsearch6 import helpers as es6_helpers
from elasticsearch6_dsl.connections import connections as es6_connections
from elasticsearch8.exceptions import ConnectionError as Elastic8ConnectionError
from elasticsearch_metrics.registry import djelme_registry
from elasticsearch_metrics.imps import elastic8 as djel8me
from psycopg2 import OperationalError as PostgresOperationalError

from framework.celery_tasks import app as celery_app
from osf.metrics.preprint_metrics import (
    PreprintView,
    PreprintDownload,
)
from osf.metrics.counted_usage import CountedAuthUsage as CountedUsageEs6
from osf.metrics import reports as es6_reports
from osf.metrics import es8_metrics, RegistriesModerationMetrics
from osf.metrics.reporters.public_item_usage import _iter_composite_bucket_keys
from osf.metrics.utils import YearMonth
from osf import models as osfdb
from website import settings as website_settings


_logger = logging.getLogger(__name__)

###
# constants

_USAGE_DAYS_BACK = 99

_MAX_CARDINALITY_PRECISION = 40000  # https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-metrics-cardinality-aggregation.html#_precision_control

_UNCHANGED_RECORDTYPES = {
    # reports
    es6_reports.StorageAddonUsage: es8_metrics.StorageAddonUsageEs8,
    es6_reports.DownloadCountReport: es8_metrics.DownloadCountReportEs8,
    es6_reports.InstitutionSummaryReport: es8_metrics.InstitutionSummaryReportEs8,
    es6_reports.NewUserDomainReport: es8_metrics.NewUserDomainReportEs8,
    es6_reports.NodeSummaryReport: es8_metrics.NodeSummaryReportEs8,
    es6_reports.OsfstorageFileCountReport: es8_metrics.OsfstorageFileCountReportEs8,
    es6_reports.PreprintSummaryReport: es8_metrics.PreprintSummaryReportEs8,
    es6_reports.UserSummaryReport: es8_metrics.UserSummaryReportEs8,
    es6_reports.SpamSummaryReport: es8_metrics.SpamSummaryReportEs8,
    es6_reports.InstitutionalUserReport: es8_metrics.InstitutionalUserReportEs8,
    es6_reports.InstitutionMonthlySummaryReport: es8_metrics.InstitutionMonthlySummaryReportEs8,
    es6_reports.PrivateSpamMetricsReport: es8_metrics.PrivateSpamMetricsReportEs8,
    # events
    RegistriesModerationMetrics: es8_metrics.RegistriesModerationMetricsEs8,
}

_TASK_KWARGS = dict(
    autoretry_for=(
        DjangoOperationalError,
        Elastic6ConnectionError,
        Elastic8ConnectionError,
        PostgresOperationalError,
    ),
    retry_backoff=True,  # exponential backoff, with jitter
    max_retries=20,
)

###
# celery tasks


@celery_app.task(**_TASK_KWARGS)
def migrate_unchanged_recordtype(es6_recordtype_name: str, until_when: str):
    _es6_recordtype = djelme_registry.get_recordtype('osf', es6_recordtype_name)
    _es8_recordtype = _UNCHANGED_RECORDTYPES[_es6_recordtype]
    _convert_kwargs = (
        _convert_unchanged_cyclicrecord_kwargs
        if issubclass(_es8_recordtype, djel8me.CyclicRecord)
        else (lambda _kw: _kw)  # no conversion needed for event record
    )
    _each_new = (
        _es8_recordtype(**_convert_kwargs(_hit['_source']))
        for _hit in _es6_scan_range(_es6_recordtype, until_when=until_when)
    )
    return _es8_bulk_save(_es8_recordtype, _each_new)


@celery_app.task(**_TASK_KWARGS)
def migrate_counted_usages(from_when: str, until_when: str):
    # CountedAuthUsage => OsfCountedUsageRecord
    _each_new = (
        _convert_counted_usage(_hit['_source'])
        for _hit in _es6_scan_range(
            CountedUsageEs6,
            from_when=from_when,
            until_when=until_when,
            addl_filter={'exists': {'field': 'item_guid'}},
        )
    )
    return _es8_bulk_save(es8_metrics.OsfCountedUsageRecord, _each_new)


@celery_app.task(**_TASK_KWARGS)
def migrate_preprint_views(from_when: str, until_when: str):
    # PreprintView => OsfCountedUsageRecord
    _action_labels = ['view', 'web']
    _each_new = (
        _convert_preprint_metric(_hit['_source'], _action_labels)
        for _hit in _es6_scan_range(
            PreprintView, from_when=from_when, until_when=until_when
        )
    )
    return _es8_bulk_save(es8_metrics.OsfCountedUsageRecord, _each_new)


@celery_app.task(**_TASK_KWARGS)
def migrate_preprint_downloads(from_when: str, until_when: str):
    # PreprintDownload => OsfCountedUsageRecord
    _action_labels = ['download']
    _each_new = (
        _convert_preprint_metric(_hit['_source'], _action_labels)
        for _hit in _es6_scan_range(
            PreprintDownload, from_when=from_when, until_when=until_when
        )
    )
    return _es8_bulk_save(es8_metrics.OsfCountedUsageRecord, _each_new)


@celery_app.task(**_TASK_KWARGS)
def migrate_usage_reports(osfid: str, until_when: str):
    # from PublicItemUsageReport to PublicItemUsageReportEs8
    def _each_new():
        # go in sorted order to build cumulative counts
        # (only a few dozen of these per item; should be fine to sort and load all at once)
        _each_hit = _es6_scan_range(
            es6_reports.PublicItemUsageReport,
            until_when=until_when,
            addl_filter={'term': {'item_osfid': osfid}},
            sort='report_yearmonth',
        )
        _prior_report = None
        for _hit in list(_each_hit):
            yield (
                _prior_report := _convert_public_usage_report(
                    _hit['_source'], _prior_report
                )
            )

    return _es8_bulk_save(es8_metrics.PublicItemUsageReportEs8, _each_new())


###
# various helper functions


def _es6_connection():
    return es6_connections.get_connection('osfmetrics_es6')


def _es8_bulk_save(es8_recordtype, each_new_record):
    _success_count, _fail_count = es8_recordtype.bulk(
        each_new_record,
        stats_only=True,
    )
    return _success_count


def _date_range(
    range_start: datetime.date,
    range_end: datetime.date,
    step: datetime.timedelta = datetime.timedelta(days=1),
) -> collections.abc.Iterator[tuple[datetime.date, datetime.date]]:
    _from_date = range_start
    _until_date = range_start + step
    while _from_date < range_end:
        yield (_from_date, _until_date)
        (_from_date, _until_date) = (_until_date, _until_date + step)


def _es6_scan_range(
    es6_recordtype,
    *,
    from_when: str = '',
    until_when: str,
    addl_filter=None,
    sort=None,
):
    _timestamp_range = {'lt': until_when}
    if from_when:
        _timestamp_range['gte'] = from_when
    _filters = [
        {'range': {'timestamp': _timestamp_range}},
    ]
    if addl_filter:
        _filters.append(addl_filter)
    _query_body = {'query': {'bool': {'filter': _filters}}}
    if sort:
        _query_body['sort'] = sort
    return es6_helpers.scan(
        _es6_connection(),
        index=es6_recordtype._template_pattern,
        query=_query_body,
    )


def _es6_usage_report_counts() -> tuple[int, int]:
    _search = es6_reports.PublicItemUsageReport.search()
    _search.aggs.metric(
        'agg_item_count',
        'cardinality',
        field='item_osfid',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total
    _item_count = (
        _response.aggregations.agg_item_count.value
        if 'agg_item_count' in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


def _es8_usage_report_counts() -> tuple[int, int]:
    _search = es8_metrics.PublicItemUsageReportEs8.search()
    _search.aggs.metric(
        'agg_item_count',
        'cardinality',
        field='item_osfid',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total.value
    _item_count = (
        _response.aggregations.agg_item_count.value
        if 'agg_item_count' in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


def _get_es6_field_names(es6_recordtype):
    '''
    adapted from DocumentBase._get_field_names in elasticsearch8.dsl
    '''
    for _field_name in es6_recordtype._doc_type.mapping:
        _field = es6_recordtype._doc_type.mapping[_field_name]
        if hasattr(_field, '_doc_class'):
            for _sub_field in _get_es6_field_names(_field._doc_class):
                yield f'{_field_name}.{_sub_field}'
        else:
            yield _field_name


def _assert_field_unchangedness(es6_recordtype, es8_recordtype):
    _es6_fields = set(_get_es6_field_names(es6_recordtype))
    _es8_fields = set(es8_recordtype._get_field_names())

    # remove fields intentionally removed in migration
    if issubclass(es6_recordtype, es6_reports.DailyReport):
        assert issubclass(es8_recordtype, djel8me.CyclicRecord)
        _es6_fields.remove('timestamp')
        _es6_fields.remove('report_date')
    elif issubclass(es6_recordtype, es6_reports.MonthlyReport):
        assert issubclass(es8_recordtype, djel8me.CyclicRecord)
        _es6_fields.remove('timestamp')
        _es6_fields.remove('report_yearmonth')
    else:
        assert issubclass(es8_recordtype, djel8me.EventRecord)

    # remove fields intentionally added in migration
    _es8_fields.remove('timeseries_timeparts')
    if issubclass(es8_recordtype, djel8me.CyclicRecord):
        _es8_fields.remove('created')
        _es8_fields.remove('cycle_coverage')

    # all remaining fields should match
    assert _es6_fields == _es8_fields


def _semverish_from_yearmonth(given_yearmonth: str):
    _ym = YearMonth.from_str(given_yearmonth)
    return f'{_ym.year}.{_ym.month}'


def _semverish_from_date(given_date: str):
    _d = datetime.date.fromisoformat(given_date)
    return f'{_d.year}.{_d.month}.{_d.day}'


def _convert_unchanged_cyclicrecord_kwargs(es6_source: dict) -> dict:
    def _each_kwarg():
        for _key, _val in es6_source.items():
            if _key == 'report_yearmonth':
                # report_yearmonth converts to cycle_coverage Y.M
                yield ('cycle_coverage', _semverish_from_yearmonth(_val))
            elif _key == 'report_date':
                # report_date converts to cycle_coverage Y.M.D
                yield ('cycle_coverage', _semverish_from_date(_val))
            elif _key != 'timestamp':
                # skipping timestamp; on daily/monthly reports just copied from yearmonth/date
                yield (_key, _val)

    return dict(_each_kwarg())


def _convert_counted_usage(source: dict) -> es8_metrics.OsfCountedUsageRecord:
    _item_iri = _iri_from_osfid(source['item_guid'])
    return es8_metrics.OsfCountedUsageRecord(
        # fields from djelme.CountedUsageRecord:
        timestamp=source['timestamp'],
        sessionhour_id=source['session_id'],
        platform_iri=source.get('platform_iri') or website_settings.DOMAIN,
        database_iri=_convert_database_iri(
            source.get('provider_id'), source.get('item_type')
        ),
        item_iri=_item_iri,
        within_iris=[
            _iri_from_osfid(_within_osfid)
            for _within_osfid in source.get('surrounding_guids', ())
        ],
        # fields from OsfCountedUsageRecord:
        item_osfid=source['item_guid'],
        item_type=source.get('item_type', 'osf:Object'),
        item_public=source.get('item_public'),
        provider_id=source.get('provider_id'),
        user_is_authenticated=source.get('user_is_authenticated'),
        action_labels=source.get('action_labels'),
        pageview_info=source.get('pageview_info'),
    )


def _convert_preprint_metric(
    source: dict, action_labels: list[str]
) -> es8_metrics.OsfCountedUsageRecord:
    _preprint_iri = _iri_from_osfid(source['preprint_id'])
    return es8_metrics.OsfCountedUsageRecord.record(
        using=False,  # don't save yet; will save in bulk
        # fields used to compute a sessionhour_id:
        timestamp=datetime.datetime.fromisoformat(source['timestamp']),
        user_id=source.get('user_id'),
        client_session_id=str(uuid.uuid4()),
        # fields from djelme.CountedUsageRecord:
        platform_iri=website_settings.DOMAIN,
        database_iri=_convert_database_iri(source.get('provider_id'), 'preprint'),
        item_iri=_preprint_iri,
        within_iris=[_preprint_iri],
        # fields from OsfCountedUsageRecord:
        item_osfid=source['preprint_id'],
        item_type='preprint',
        item_public=True,
        provider_id=source.get('provider_id'),
        user_is_authenticated=bool(source.get('user_id')),
        action_labels=action_labels,
    )


def _convert_public_usage_report(
    source: dict,
    prior_report: es8_metrics.PublicItemUsageReportEs8 | None,
) -> es8_metrics.PublicItemUsageReportEs8:
    if prior_report is None:
        _c_views, _c_view_sess, _c_downloads, _c_download_sess = _get_cumulative_usage(
            osfid=source['item_osfid'],
            until_when=YearMonth.from_str(source['report_yearmonth']).month_end(),
            item_type=source.get('item_type'),
        )
    else:
        _c_views = prior_report.cumulative_view_count + source.get('view_count', 0)
        _c_view_sess = prior_report.cumulative_view_session_count + source.get(
            'view_session_count', 0
        )
        _c_downloads = prior_report.cumulative_download_count + source.get(
            'download_count', 0
        )
        _c_download_sess = prior_report.cumulative_download_session_count + source.get(
            'download_session_count', 0
        )
    return es8_metrics.PublicItemUsageReportEs8(
        cycle_coverage=_semverish_from_yearmonth(source['report_yearmonth']),
        item_osfid=source['item_osfid'],
        item_type=source.get('item_type'),
        provider_id=source.get('provider_id'),
        platform_iri=source.get('platform_iri') or website_settings.DOMAIN,
        view_count=source.get('view_count'),
        view_session_count=source.get('view_session_count'),
        cumulative_view_count=_c_views,
        cumulative_view_session_count=_c_view_sess,
        download_count=source.get('download_count'),
        download_session_count=source.get('download_session_count'),
        cumulative_download_count=_c_downloads,
        cumulative_download_session_count=_c_download_sess,
    )


def _get_cumulative_usage(osfid: str, until_when, item_type: str | None):
    if item_type == 'preprint':
        _views = _cumulative_preprint_count(PreprintView, osfid, until_when)
        _downloads = _cumulative_preprint_count(PreprintDownload, osfid, until_when)
        _view_sess, _download_sess = 0, 0  # no session info on preprints (yet)
    else:
        _views, _view_sess = _cumulative_countedusage_views(osfid, until_when)
        _downloads, _download_sess = _cumulative_countedusage_downloads(
            osfid, until_when
        )
    return (_views, _view_sess, _downloads, _download_sess)


def _cumulative_countedusage_views(osfid: str, until_when: str) -> tuple[int, int]:
    '''compute view_session_count separately to avoid double-counting

    (the same session may be represented in both the composite agg on `item_guid`
    and that on `surrounding_guids`)
    '''
    # copied/adapted from osf.metrics.reporters.public_item_usage
    _search = (
        CountedUsageEs6.search()
        .filter('term', item_public=True)
        .filter('range', timestamp={'lt': until_when})
        .filter('term', action_labels='view')
        .filter(
            'bool',
            should=[
                {'term': {'item_guid': osfid}},
                {'term': {'surrounding_guids': osfid}},
            ],
            minimum_should_match=1,
        )
        .extra(size=0)  # only aggregations, no hits
    )
    _search.aggs.metric(
        'agg_session_count',
        'cardinality',
        field='session_id',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _view_count = _response.hits.total
    _view_session_count = (
        _response.aggregations.agg_session_count.value
        if 'agg_session_count' in _response.aggregations
        else 0
    )
    return (_view_count, _view_session_count)


def _cumulative_countedusage_downloads(osfid, until_when) -> tuple[int, int]:
    '''aggregate downloads on each osfid (not including components/files)'''
    # copied/adapted from osf.metrics.reporters.public_item_usage
    _search = (
        CountedUsageEs6.search()
        .filter('term', item_public=True)
        .filter('range', timestamp={'lt': until_when})
        .filter('term', action_labels='download')
        .filter('term', item_guid=osfid)
    )
    _search.aggs.metric(
        'agg_session_count',
        'cardinality',
        field='session_id',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _download_count = _response.hits.total
    _download_session_count = (
        _response.aggregations.agg_session_count.value
        if 'agg_session_count' in _response.aggregations
        else 0
    )
    return (_download_count, _download_session_count)


def _cumulative_preprint_count(preprint_metric_cls, osfid: str, until_when: str) -> int:
    '''aggregate views on each preprint'''
    # copied/adapted from osf.metrics.preprint_metrics
    _search = (
        preprint_metric_cls.search()
        .filter('term', preprint_id=osfid)
        .filter('range', timestamp={'lt': until_when})
        .extra(size=0)  # no hits; only aggs
    )
    _search.aggs.metric('agg_count', 'sum', field='count')
    _response = _search.execute()
    _view_count = (
        int(_response.aggregations.agg_count.value)
        if hasattr(_response.aggregations, 'agg_count')
        else 0
    )
    return _view_count


def _iri_from_osfid(osfid: str) -> str:
    return f'{website_settings.DOMAIN}{osfid}'


@functools.lru_cache
def _convert_database_iri(provider_id: str | None, item_type: str) -> str:
    if not provider_id:
        return website_settings.DOMAIN  # osf is a provider, sure why not

    def _fallback_iri():
        return f'urn:osf.io:{provider_id}'

    match item_type:  # lower-cased osf.models class names
        case 'node' | 'osfuser':
            # implicit 'osf' provider
            return website_settings.DOMAIN
        case 'preprint':
            try:
                _provider = osfdb.PreprintProvider.objects.get(_id=provider_id)
            except osfdb.PreprintProvider.DoesNotExist:
                _logger.error(f'unknown preprint provider {provider_id!r}')
                return _fallback_iri()
            else:
                return _provider.get_semantic_iri()
        case 'registration':
            try:
                _provider = osfdb.RegistrationProvider.objects.get(_id=provider_id)
            except osfdb.RegistrationProvider.DoesNotExist:
                _logger.error(f'unknown registration provider {provider_id!r}')
                return _fallback_iri()
            else:
                return _provider.get_semantic_iri()
        case _ if 'file' in item_type:
            # file providers are a different thing that don't really have an iri, just an id
            return f'urn:files.osf.io:{provider_id}'
        case _:  # give up gracefully
            _logger.error(
                f'unknown item type {item_type!r} with provider {provider_id!r}'
            )
            return _fallback_iri()


def _each_usage_report_osfid(until_when, after_osfid=None):
    _search = (
        es6_reports.PublicItemUsageReport.search()
        .filter('range', timestamp={'lt': until_when})
        .extra(size=0)
    )
    _search.aggs.bucket(
        'agg_osfid',
        'composite',
        sources=[{'osfid': {'terms': {'field': 'item_osfid'}}}],
        size=500,
    )
    return _iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)


###
# the command itself


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--no-setup',
            action='store_true',
        )
        parser.add_argument(
            '--no-counts',
            action='store_true',
        )
        parser.add_argument(
            '--clear-state',
            action='store_true',
        )
        parser.add_argument(
            '--start',
            action='store_true',
        )
        parser.add_argument(
            '--unchanged',
            action='store_true',
        )
        parser.add_argument(
            '--usage-events',
            action='store_true',
        )
        parser.add_argument(
            '--usage-reports',
            action='store_true',
        )

    @functools.cached_property
    def _migration_started_at(self):
        return es8_metrics.Elastic6To8State.get_started_at()

    def handle(
        self,
        *,
        no_setup,
        no_counts,
        clear_state,
        start,
        unchanged,
        usage_events,
        usage_reports,
        **kwargs,
    ):
        self._quiet_chatty_loggers()
        if not no_setup:
            call_command('djelme_backend_setup')
        if clear_state:
            self._clear_state()
        self._check_started_at(start_now=start)
        _default_all = not any((unchanged, usage_events, usage_reports))
        if unchanged or _default_all:
            self._handle_unchanged(start=start, no_counts=no_counts)
        if usage_events or _default_all:
            self._handle_usage_events(start=start, no_counts=no_counts)
        if usage_reports or _default_all:
            self._handle_usage_reports(start=start, no_counts=no_counts)
        if not no_counts:
            self.stdout.write('(counts may be approximate)')

    def _handle_unchanged(self, *, start: bool, no_counts: bool):
        # for each (unchanged) report/event:
        for _es6_cls, _es8_cls in _UNCHANGED_RECORDTYPES.items():
            _assert_field_unchangedness(_es6_cls, _es8_cls)
            if not no_counts:
                # display counts
                _es6_count = _es6_cls.search().count()
                _es8_count = _es8_cls.search().count()
                self._write_tabbed('es6', _es6_cls, _es6_count)
                self._write_tabbed(
                    'es8',
                    _es8_cls,
                    _es8_count,
                    style=self._eq_style(_es8_count, _es6_count),
                )
            if start:  # schedule task
                self.stdout.write(
                    f'starting {_es6_cls.__name__} => {_es8_cls.__name__}'
                )
                migrate_unchanged_recordtype.delay(
                    _es6_cls.__name__, self._migration_started_at.isoformat()
                )

    def _handle_usage_events(self, *, start: bool, no_counts: bool):
        # for counted-usage events:
        _started = self._migration_started_at or datetime.datetime.now()
        _range_start = (_started - datetime.timedelta(days=_USAGE_DAYS_BACK)).date()
        _range_end = _started.date() + datetime.timedelta(days=1)
        if not no_counts:
            # display counts for each view/download event type
            _range_q = {
                'range': {
                    'timestamp': {
                        'gte': _range_start.isoformat(),
                        'lt': _range_end.isoformat(),
                    }
                }
            }
            _es6_pview_count = PreprintView.search().filter(_range_q).count()
            _es6_pdownload_count = PreprintDownload.search().filter(_range_q).count()
            _es6_usage_event_count = CountedUsageEs6.search().filter(_range_q).count()
            _es6_count = (
                _es6_pview_count + _es6_pdownload_count + _es6_usage_event_count
            )
            _es8_count = es8_metrics.OsfCountedUsageRecord.search().count()
            self._write_tabbed('es6', PreprintView, _es6_pview_count)
            self._write_tabbed('es6', PreprintDownload, _es6_pdownload_count)
            self._write_tabbed('es6', CountedUsageEs6, _es6_usage_event_count)
            self._write_tabbed(
                'es6', f'(total between {_range_start} and {_range_end})', _es6_count
            )
            self._write_tabbed(
                'es8',
                es8_metrics.OsfCountedUsageRecord,
                _es8_count,
                style=self._eq_style(_es8_count, _es6_count),
            )
        if start:  # schedule (per-day?) tasks (if --start)
            self.stdout.write(
                f'starting usages => {es8_metrics.OsfCountedUsageRecord.__name__}'
            )
            for _from_date, _until_date in _date_range(_range_start, _range_end):
                _from_str = _from_date.isoformat()
                _until_str = _until_date.isoformat()
                migrate_counted_usages.delay(_from_str, _until_str)
                migrate_preprint_views.delay(_from_str, _until_str)
                migrate_preprint_downloads.delay(_from_str, _until_str)

    def _handle_usage_reports(self, *, start: bool, no_counts: bool):
        if not no_counts:
            # display counts of reports and distinct items
            _es6_count, _es6_item_count = _es6_usage_report_counts()
            _es8_count, _es8_item_count = _es8_usage_report_counts()
            self._write_tabbed('es6', es6_reports.PublicItemUsageReport, _es6_count)
            self._write_tabbed(
                'es8',
                es8_metrics.PublicItemUsageReportEs8,
                _es8_count,
                style=self._eq_style(_es8_count, _es6_count),
            )
            self._write_tabbed(
                'es6',
                es6_reports.PublicItemUsageReport,
                'osfid count:',
                _es6_item_count,
            )
            self._write_tabbed(
                'es8',
                es8_metrics.PublicItemUsageReportEs8,
                '(items)',
                _es8_item_count,
                style=self._eq_style(_es8_item_count, _es6_item_count),
            )
        # (if --start) schedule task per item (by composite agg on es6 public usage reports)
        # each item-task iter thru reports oldest to newest, adding cumulative counts
        if start:
            self.stdout.write(
                f'starting per-item {es6_reports.PublicItemUsageReport.__name__} => {es8_metrics.PublicItemUsageReportEs8.__name__}'
            )
            for _osfid in _each_usage_report_osfid(
                until_when=self._migration_started_at
            ):
                migrate_usage_reports.delay(
                    _osfid, self._migration_started_at.isoformat()
                )

    def _check_started_at(self, start_now):
        _started_at = self._migration_started_at
        if _started_at:
            self.stdout.write(
                f'osf.metrics 6->8 migration started previously, at {_started_at.isoformat()}'
            )
        elif start_now:
            _started_at = es8_metrics.Elastic6To8State.set_started_at_now()
            del self._migration_started_at  # clear cache
            self.stdout.write(
                f'osf.metrics 6->8 migration starting now, at {_started_at.isoformat()}'
            )
        else:
            self.stdout.write(
                'osf.metrics 6->8 migration not started nor starting (run with `--start` to start)'
            )

    def _clear_state(self):
        self.stdout.write(
            'clearing all migration state (start time, etc)', self.style.NOTICE
        )
        es8_metrics.Elastic6To8State.search().query({'match_all': {}}).delete()
        es8_metrics.Elastic6To8State.refresh()

    def _eq_style(self, num: int, should_be: int):
        return self.style.SUCCESS if (num == should_be) else self.style.WARNING

    def _write_tabbed(self, *strables, style=None):
        def _to_str(strable):
            if isinstance(strable, type):
                return strable.__name__
            return str(strable)

        self.stdout.write('\t'.join(map(_to_str, strables)), style)

    def _quiet_chatty_loggers(self):
        _chatty_loggers = [
            'elasticsearch',
            'elastic_transport',
            'elasticsearch_metrics',
        ]
        for logger_name in _chatty_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
