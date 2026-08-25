import collections
import heapq
import itertools
import logging

from django.conf import settings as api_settings
from django.core.management.base import BaseCommand
from django.db import OperationalError as DjangoOperationalError
from elasticsearch6.exceptions import ConnectionError as Elastic6ConnectionError
from elasticsearch8.exceptions import TransportError as Elastic8TransportError
from psycopg2 import OperationalError as PostgresOperationalError

from framework.celery_tasks import app as celery_app
from framework.sentry import log_exception
from osf.metrics import es6_metrics
from osf.metrics.monthly_reports import MonthlyPublicItemUsageReport
from osf.metrics.utils import (
    YearMonth,
    get_database_iri,
    get_item_type,
    iter_composite_bucket_keys,
)
from osf import models as osfdb
from osf.models.base import osfid_iri
from website import settings as website_settings


###
# constants

_EPOCH_YEARMONTH = YearMonth.from_str(api_settings.MONTHLY_USAGE_REPORT_EPOCH)

_MAX_CARDINALITY_PRECISION = 40000  # https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-metrics-cardinality-aggregation.html#_precision_control

_COMPOSITE_CHUNK_SIZE = 500

_RETRY_ERRORS = (
    DjangoOperationalError,
    Elastic6ConnectionError,
    Elastic8TransportError,
    PostgresOperationalError,
)
_TASK_KWARGS = dict(
    autoretry_for=_RETRY_ERRORS,
    retry_backoff=True,  # exponential backoff, with jitter
    max_retries=20,
)


###
# fix usage report migration

@celery_app.task(**_TASK_KWARGS)
def schedule_fix_usage_reports(after_osfid: str | None = None):
    _until_when = _EPOCH_YEARMONTH.month_end()
    _last_osfid = None
    try:
        for _osfid in _merge_sorted_osfids(
            _each_countedusage_osfid(_until_when, after_osfid),
            _each_preprintview_osfid(_until_when, after_osfid),
            _each_preprintdownload_osfid(_until_when, after_osfid),
        ):
            add_fixed_usage_reports.delay(_osfid)
            _last_osfid = _osfid
    except _RETRY_ERRORS as _error:
        if _last_osfid is None:
            raise  # didn't even get started
        # schedule another task to continue scheduling
        schedule_fix_usage_reports.delay(
            after_osfid=(  # avoid infinite loop from _merge_sorted_osfids removing "_v1"
                f'{_last_osfid}_v1'
                if '_' not in _last_osfid
                else _last_osfid
            ),
        )
        # let this task succeed but log the error
        log_exception(_error)


@celery_app.task(**_TASK_KWARGS)
def add_fixed_usage_reports(osfid: str):
    # from PublicItemUsageReport to MonthlyPublicItemUsageReportEs8
    _osfobj, _ = osfdb.Guid.load_referent(osfid)
    if isinstance(_osfobj, osfdb.Preprint) and '_' not in osfid:
        osfid = f'{osfid}_v1'
        _osfobj, _ = osfdb.Guid.load_referent(osfid)
    if _osfobj:
        _months = _months_with_usage(osfid, _osfobj, _EPOCH_YEARMONTH.month_end())
        _months.add(_EPOCH_YEARMONTH)  # guarantee at least the one
        for _ym in _months:
            _usage_report = _make_usage_report(osfid, _osfobj, _ym)
            _usage_report.save()
    else:
        raise RuntimeError('osfid does not exist! skipping...', osfid)


###
# various helper functions

def _yearmonth_range_to_epoch(start):
    _ym = max(YearMonth.from_any(start), YearMonth(2026, 1))
    while _ym <= _EPOCH_YEARMONTH:
        yield _ym
        _ym = _ym.next()


def _months_with_usage(osfid, osf_obj, until_when) -> set[YearMonth]:
    _months = set()
    if isinstance(osf_obj, osfdb.Preprint):
        _searches = [
            _es6_osfid_preprint_event_search(es6_metrics.PreprintView, osfid, until_when),
            _es6_osfid_preprint_event_search(es6_metrics.PreprintDownload, osfid, until_when),
        ]
    else:
        _searches = [
            _es6_osfid_nonpreprint_view_search(osfid, until_when),
            _es6_osfid_nonpreprint_download_search(osfid, until_when),
        ]
    for _search in _searches:
        _search.aggs.bucket(
            'agg_months',
            'date_histogram',
            field='timestamp',
            interval='month',
            format='yyyy-MM',
            min_doc_count=1,
        )
        _response = _search.execute()
        if 'agg_months' in _response.aggregations:
            _months.update(
                YearMonth.from_str(_bucket.key_as_string)
                for _bucket in _response.aggregations.agg_months.buckets
            )
    return _months


def _semverish_from_yearmonth(given_yearmonth):
    _ym = YearMonth.from_any(given_yearmonth)
    return f'{_ym.year}.{_ym.month}'


def _make_usage_report(osfid: str, osf_obj, yearmonth: YearMonth):
    # add a report for the given month with cumulative counts up to that point
    _is_preprint = isinstance(osf_obj, osfdb.Preprint)
    # cumulative counts
    _c_views, _c_view_sess, _c_downloads, _c_download_sess = _get_cumulative_usage(
        osfid=osfid,
        until_when=yearmonth.month_end().isoformat(),
        is_preprint=_is_preprint,
    )
    # counts for that month only
    _views, _view_sess, _downloads, _download_sess = _get_cumulative_usage(
        osfid=osfid,
        until_when=yearmonth.month_end().isoformat(),
        from_when=yearmonth.month_start().isoformat(),
        is_preprint=_is_preprint,
    )
    return MonthlyPublicItemUsageReport(
        cycle_coverage=_semverish_from_yearmonth(yearmonth),
        item_iri=osfid_iri(osfid),
        item_osfids=[osfid],
        item_types=[get_item_type(osf_obj)],
        provider_ids=[_get_provider_id(osf_obj)],
        database_iris=[get_database_iri(osf_obj)],
        platform_iris=[website_settings.DOMAIN],
        view_count=_views,
        view_session_count=_view_sess,
        cumulative_view_count=_c_views,
        cumulative_view_session_count=_c_view_sess,
        download_count=_downloads,
        download_session_count=_download_sess,
        cumulative_download_count=_c_downloads,
        cumulative_download_session_count=_c_download_sess,
    )


def _get_provider_id(osfid_referent):
    _provider = getattr(osfid_referent, 'provider', None)
    if _provider is None:
        return 'osf'          # quacks like Node, Comment, WikiPage
    elif isinstance(_provider, str):
        return _provider      # quacks like BaseFileNode
    else:
        return _provider._id  # quacks like Registration, Preprint, Collection


def _get_cumulative_usage(osfid: str, *, until_when, from_when='', is_preprint: bool):
    if is_preprint:
        _views = _cumulative_preprint_count(
            es6_metrics.PreprintView,
            osfid,
            until_when=until_when,
            from_when=from_when,
        )
        _downloads = _cumulative_preprint_count(
            es6_metrics.PreprintDownload,
            osfid,
            until_when=until_when,
            from_when=from_when,
        )
        _view_sess, _download_sess = _views, _downloads  # no session info on preprints (yet)
    else:
        _views, _view_sess = _cumulative_countedusage_views(
            osfid,
            until_when=until_when,
            from_when=from_when,
        )
        _downloads, _download_sess = _cumulative_countedusage_downloads(
            osfid,
            until_when=until_when,
            from_when=from_when,
        )
    return (_views, _view_sess, _downloads, _download_sess)


def _cumulative_countedusage_views(
    osfid: str, *, until_when: str, from_when: str = ''
) -> tuple[int, int]:
    # copied/adapted from osf.metrics.reporters.public_item_usage
    _search = (
        _es6_osfid_nonpreprint_view_search(osfid, until_when)
        .extra(size=0)  # only aggregations, no hits
    )
    if from_when:
        _search = _search.filter('range', timestamp={'gte': from_when})
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


def _es6_preprint_event_search(preprint_metric_cls, until_when, from_when=None):
    _search = (
        preprint_metric_cls.search()
        .filter('range', timestamp={'lt': until_when})
        .extra(size=0)  # no hits; only aggs
    )
    if from_when:
        _search = _search.filter('range', timestamp={'gte': from_when})
    return _search


def _es6_osfid_preprint_event_search(preprint_metric_cls, osfid, until_when, from_when=None):
    return (
        _es6_preprint_event_search(preprint_metric_cls, until_when, from_when)
        .filter('terms', preprint_id=_synonymous_osfids(osfid))
    )

def _es6_nonpreprint_event_search(until_when, from_when='', *, action_labels=None):
    _search = (
        es6_metrics.CountedAuthUsage.search()
        .filter('term', item_public=True)
        .filter('terms', action_labels=(action_labels or ['view', 'download']))
        .filter('range', timestamp={'lt': until_when})
        .extra(size=0)  # only aggregations, no hits
    )
    if from_when:
        _search = _search.filter('range', timestamp={'gte': from_when})
    return _search


def _es6_nonpreprint_download_search(until_when, from_when=''):
    return _es6_nonpreprint_event_search(until_when, from_when, action_labels=['download'])


def _es6_osfid_nonpreprint_download_search(osfid, until_when, from_when=''):
    return (
        _es6_nonpreprint_download_search(until_when, from_when)
        .filter('term', item_guid=osfid)
    )


def _es6_nonpreprint_view_search(until_when, from_when=''):
    return _es6_nonpreprint_event_search(until_when, from_when, action_labels=['view'])


def _es6_osfid_nonpreprint_view_search(osfid, until_when, from_when=''):
    return (
        _es6_nonpreprint_view_search(until_when, from_when)
        .filter(
            'bool',
            should=[
                {'term': {'item_guid': osfid}},
                {'term': {'surrounding_guids': osfid}},
            ],
            minimum_should_match=1,
        )
    )


def _cumulative_countedusage_downloads(osfid, *, until_when, from_when) -> tuple[int, int]:
    '''aggregate downloads on each osfid (not including components/files)'''
    # copied/adapted from osf.metrics.reporters.public_item_usage
    _search = _es6_osfid_nonpreprint_download_search(osfid, until_when, from_when)
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


def _cumulative_preprint_count(
    preprint_metric_cls, osfid: str, *, until_when: str, from_when: str = ''
) -> int:
    '''aggregate counts on given preprint'''
    # copied/adapted from osf.metrics.preprint_metrics
    _search = _es6_osfid_preprint_event_search(preprint_metric_cls, osfid, until_when, from_when)
    _search.aggs.metric('agg_count', 'sum', field='count')
    _response = _search.execute()
    return (
        int(_response.aggregations.agg_count.value)
        if hasattr(_response.aggregations, 'agg_count')
        else 0
    )


def _synonymous_osfids(osfid: str) -> list[str]:
    _synonyms = [osfid]
    if osfid.endswith('_v1'):
        # include pre-versioned-guid counts for v1
        _synonyms.append(osfid.removesuffix('_v1'))
    elif '_' not in osfid:
        # include v1 (if it exists) with unversioned guid
        _synonyms.append(f'{osfid}_v1')
    return _synonyms


def _each_countedusage_osfid(until_when, after_osfid=None) -> collections.abc.Iterator[str]:
    _search = _es6_nonpreprint_event_search(until_when)
    _search.aggs.bucket(
        'agg_osfid',
        'composite',
        sources=[{'osfid': {'terms': {'field': 'item_guid'}}}],
        size=_COMPOSITE_CHUNK_SIZE,
    )
    return iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)


def _each_preprintview_osfid(until_when, after_osfid=None) -> collections.abc.Iterator[str]:
    _search = _es6_preprint_event_search(es6_metrics.PreprintView, until_when)
    _search.aggs.bucket(
        'agg_osfid',
        'composite',
        sources=[{'osfid': {'terms': {'field': 'preprint_id'}}}],
        size=_COMPOSITE_CHUNK_SIZE,
    )
    return iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)


def _each_preprintdownload_osfid(until_when, after_osfid=None) -> collections.abc.Iterator[str]:
    _search = _es6_preprint_event_search(es6_metrics.PreprintDownload, until_when)
    _search.aggs.bucket(
        'agg_osfid',
        'composite',
        sources=[{'osfid': {'terms': {'field': 'preprint_id'}}}],
        size=_COMPOSITE_CHUNK_SIZE,
    )
    return iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)


def _merge_sorted_osfids(*osfid_iterables):
    def _osfids_group_key(osfid: str):
        return (  # v1 same as unversioned
            osfid.removesuffix('_v1')
            if osfid.endswith('_v1')
            else osfid
        )
    for _k, _g in itertools.groupby(
        heapq.merge(*osfid_iterables),
        key=_osfids_group_key,
    ):
        yield _k


def _es8_usage_report_count(yearmonth: YearMonth) -> int:
    _search = (
        MonthlyPublicItemUsageReport.search()
        .filter('term', cycle_coverage=_semverish_from_yearmonth(yearmonth))
        .extra(track_total_hits=True)
    )
    _response = _search.execute()
    _total_count = _response.hits.total.value
    return _total_count


def _es8_usage_report_osfid_count() -> int:
    _search = (
        MonthlyPublicItemUsageReport.search()
        .filter('range', cycle_coverage={'lte': _semverish_from_yearmonth(_EPOCH_YEARMONTH)})
        .extra(size=0)  # only aggs, no hits
    )
    _search.aggs.metric(
        'agg_osfid_count',
        'cardinality',
        field='item_osfids',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    return (
        _response.aggregations.agg_osfid_count.value
        if 'agg_osfid_count' in _response.aggregations
        else 0
    )


def _es6_preprint_osfid_count(preprint_metric_cls) -> int:
    _search = _es6_preprint_event_search(preprint_metric_cls, _EPOCH_YEARMONTH.month_end())
    _search.aggs.metric(
        'agg_osfid_count',
        'cardinality',
        field='preprint_id',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    return (
        _response.aggregations.agg_osfid_count.value
        if 'agg_osfid_count' in _response.aggregations
        else 0
    )


def _es6_cu_osfid_count() -> int:
    _search = _es6_nonpreprint_event_search(_EPOCH_YEARMONTH.month_end())
    _search.aggs.metric(
        'agg_osfid_count',
        'cardinality',
        field='item_guid',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    return (
        _response.aggregations.agg_osfid_count.value
        if 'agg_osfid_count' in _response.aggregations
        else 0
    )


###
# the command itself

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--no-counts',
            action='store_true',
        )
        parser.add_argument(
            '--start',
            action='store_true',
        )
        parser.add_argument(
            '--delete-es8-usage-reports',
            action='store_true',
        )

    def handle(self, *, start, no_counts, delete_es8_usage_reports, **kwargs):
        self._quiet_chatty_loggers()
        if delete_es8_usage_reports:
            self._delete_es8_usage_reports()
        if not no_counts:
            # display counts of reports and distinct items
            _prior_ym = _EPOCH_YEARMONTH.prior()
            self.stdout.write(
                f'total osfids with preprint views thru {_EPOCH_YEARMONTH} in es6'
                f': {_es6_preprint_osfid_count(es6_metrics.PreprintView)}'
            )
            self.stdout.write(
                f'total osfids with preprint downloads thru {_EPOCH_YEARMONTH} in es6'
                f': {_es6_preprint_osfid_count(es6_metrics.PreprintDownload)}'
            )
            self.stdout.write(
                f'total osfids with with counted usage thru {_EPOCH_YEARMONTH} in es6'
                f': {_es6_cu_osfid_count()}'
            )
            self.stdout.write(
                f'total osfids with usage reports in es8'
                f': {_es8_usage_report_osfid_count()}\t<== compare this'
            )
            self.stdout.write(
                f'total usage reports for {_prior_ym} in es8'
                f': {_es8_usage_report_count(_prior_ym)}'
            )
            self.stdout.write(
                f'total usage reports for {_EPOCH_YEARMONTH} in es8'
                f': {_es8_usage_report_count(_EPOCH_YEARMONTH)}\t<== to this'
            )
        # (if --start) schedule task per item (by composite agg on es6 usage reports and events)
        # each item-task iter thru reports oldest to newest, adding cumulative counts
        if start:
            self.stdout.write(
                f'starting per-item tasks to add a corrected usage report for {_EPOCH_YEARMONTH}'
            )
            schedule_fix_usage_reports.delay()

    def _quiet_chatty_loggers(self):
        _chatty_loggers = [
            'elasticsearch',
            'elastic_transport',
            'elasticsearch_metrics',
        ]
        for logger_name in _chatty_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)

    def _delete_es8_usage_reports(self):
        self.stdout.write('deleting monthly usage reports in es8', self.style.NOTICE)
        MonthlyPublicItemUsageReport.do_teardown(keep_templates=True)
