from __future__ import annotations
import datetime
import typing

import waffle
if typing.TYPE_CHECKING:
    import elasticsearch_dsl as edsl

import osf.features
from osf.metadata.osf_gathering import OsfmapPartition
from osf.metrics.counted_usage import (
    CountedAuthUsage,
    get_item_type,
    get_provider_id,
)
from osf.metrics.preprint_metrics import (
    PreprintDownload,
    PreprintView,
)
from osf.metrics.reports import PublicItemUsageReport
from osf.metrics.utils import YearMonth
from osf import models as osfdb
from website import settings as website_settings
from ._base import MonthlyReporter


_CHUNK_SIZE = 500

_MAX_CARDINALITY_PRECISION = 40000  # https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-metrics-cardinality-aggregation.html#_precision_control


class _SkipItem(Exception):
    pass


class PublicItemUsageReporter(MonthlyReporter):
    '''build a PublicItemUsageReport for each public item

    includes projects, project components, registrations, registration components, and preprints
    '''
    def iter_report_kwargs(self, continue_after: dict | None = None):
        _after_osfid = continue_after['osfid'] if continue_after else None
        for _osfid in _zip_sorted(
            self._countedusage_osfids(_after_osfid),
            self._preprintview_osfids(_after_osfid),
            self._preprintdownload_osfids(_after_osfid),
        ):
            yield {'osfid': _osfid}

    def report(self, **report_kwargs):
        _osfid = report_kwargs['osfid']
        # get usage metrics from several sources:
        # - osf.metrics.counted_usage:
        #   - views and downloads for each item (using `CountedAuthUsage.item_guid`)
        #   - views for each item's components and files (using `CountedAuthUsage.surrounding_guids`)
        # - osf.metrics.preprint_metrics:
        #   - preprint views and downloads
        # - PageCounter? (no)
        try:
            _guid = osfdb.Guid.load(_osfid)
            if _guid is None or _guid.referent is None:
                raise _SkipItem
            _obj = _guid.referent
            _report = self._init_report(_obj)
            self._fill_report_counts(_report, _obj)
            if not any((
                _report.view_count,
                _report.view_session_count,
                _report.download_count,
                _report.download_session_count,
            )):
                raise _SkipItem
            return _report
        except _SkipItem:
            return None

    def followup_task(self, report):
        _is_last_month = report.yearmonth.next() == YearMonth.from_date(datetime.date.today())
        if _is_last_month:
            from api.share.utils import task__update_share
            return task__update_share.s(
                report.item_osfid,
                is_backfill=True,
                osfmap_partition_name=OsfmapPartition.MONTHLY_SUPPLEMENT.name,
                countdown=30,  # give index time to settle
            )

    def _countedusage_osfids(self, after_osfid: str | None) -> typing.Iterator[str]:
        _search = self._base_usage_search()
        _search.aggs.bucket(
            'agg_osfid',
            'composite',
            sources=[{'osfid': {'terms': {'field': 'item_guid'}}}],
            size=_CHUNK_SIZE,
        )
        return _iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)

    def _preprintview_osfids(self, after_osfid: str | None) -> typing.Iterator[str]:
        _search = (
            PreprintView.search()
            .filter('range', timestamp={
                'gte': self.yearmonth.month_start(),
                'lt': self.yearmonth.month_end(),
            })
            .extra(size=0)  # only aggregations, no hits
        )
        _search.aggs.bucket(
            'agg_osfid',
            'composite',
            sources=[{'osfid': {'terms': {'field': 'preprint_id'}}}],
            size=_CHUNK_SIZE,
        )
        return _iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)

    def _preprintdownload_osfids(self, after_osfid: str | None) -> typing.Iterator[str]:
        _search = (
            PreprintDownload.search()
            .filter('range', timestamp={
                'gte': self.yearmonth.month_start(),
                'lt': self.yearmonth.month_end(),
            })
            .extra(size=0)  # only aggregations, no hits
        )
        _search.aggs.bucket(
            'agg_osfid',
            'composite',
            sources=[{'osfid': {'terms': {'field': 'preprint_id'}}}],
            size=_CHUNK_SIZE,
        )
        return _iter_composite_bucket_keys(_search, 'agg_osfid', 'osfid', after=after_osfid)

    def _init_report(self, osf_obj) -> PublicItemUsageReport:
        if not _is_item_public(osf_obj):
            raise _SkipItem
        return PublicItemUsageReport(
            item_osfid=osf_obj._id,
            item_type=[get_item_type(osf_obj)],
            provider_id=[get_provider_id(osf_obj)],
            platform_iri=[website_settings.DOMAIN],
            # leave counts null; will be set if there's data
        )

    def _fill_report_counts(self, report, osf_obj):
        if (
            isinstance(osf_obj, osfdb.Preprint)
            and not waffle.switch_is_active(osf.features.COUNTEDUSAGE_UNIFIED_METRICS_2024)  # type: ignore[attr-defined]
        ):
            # note: no session-count info in preprint metrics
            report.view_count = self._preprint_views(osf_obj)
            report.download_count = self._preprint_downloads(osf_obj)
        else:
            (
                report.view_count,
                report.view_session_count,
            ) = self._countedusage_view_counts(osf_obj)
            (
                report.download_count,
                report.download_session_count,
            ) = self._countedusage_download_counts(osf_obj)

    def _base_usage_search(self):
        return (
            CountedAuthUsage.search()
            .filter('term', item_public=True)
            .filter('range', timestamp={
                'gte': self.yearmonth.month_start(),
                'lt': self.yearmonth.month_end(),
            })
            .extra(size=0)  # only aggregations, no hits
        )

    def _countedusage_view_counts(self, osf_obj) -> tuple[int, int]:
        '''compute view_session_count separately to avoid double-counting

        (the same session may be represented in both the composite agg on `item_guid`
        and that on `surrounding_guids`)
        '''
        _search = (
            self._base_usage_search()
            .query(
                'bool',
                filter=[
                    {'term': {'action_labels': CountedAuthUsage.ActionLabel.VIEW.value}},
                ],
                should=[
                    {'term': {'item_guid': osf_obj._id}},
                    {'term': {'surrounding_guids': osf_obj._id}},
                ],
                minimum_should_match=1,
            )
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

    def _countedusage_download_counts(self, osf_obj) -> tuple[int, int]:
        '''aggregate downloads on each osfid (not including components/files)'''
        _search = (
            self._base_usage_search()
            .filter('term', item_guid=osf_obj._id)
            .filter('term', action_labels=CountedAuthUsage.ActionLabel.DOWNLOAD.value)
        )
        # agg: get download session count
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

    def _preprint_views(self, preprint: osfdb.Preprint) -> int:
        '''aggregate views on each preprint'''
        return PreprintView.get_count_for_preprint(
            preprint=preprint,
            after=self.yearmonth.month_start(),
            before=self.yearmonth.month_end(),
        )

    def _preprint_downloads(self, preprint: osfdb.Preprint) -> int:
        '''aggregate downloads on each preprint'''
        return PreprintDownload.get_count_for_preprint(
            preprint=preprint,
            after=self.yearmonth.month_start(),
            before=self.yearmonth.month_end(),
        )


def _is_item_public(osfid_referent) -> bool:
    if isinstance(osfid_referent, osfdb.Preprint):
        return bool(osfid_referent.verified_publishable)        # quacks like Preprint
    return getattr(osfid_referent, 'is_public', False)    # quacks like AbstractNode


def _zip_sorted(
    *iterators: typing.Iterator[str],
) -> typing.Iterator[str]:
    '''loop thru multiple iterators on sorted (ascending) sequences of strings
    '''
    _nexts = {  # holds the next value from each iterator, or None
        _i: next(_iter, None)
        for _i, _iter in enumerate(iterators)
    }
    while True:
        _nonnull_nexts = [
            _next
            for _next in _nexts.values()
            if _next is not None
        ]
        if not _nonnull_nexts:
            return  # all done
        _value = min(_nonnull_nexts)
        yield _value
        for _i, _iter in enumerate(iterators):
            if _nexts[_i] == _value:
                _nexts[_i] = next(_iter, None)


def _iter_composite_bucket_keys(
    search: edsl.Search,
    composite_agg_name: str,
    composite_source_name: str,
    after: str | None = None,
) -> typing.Iterator[str]:
    '''iterate thru *all* buckets of a composite aggregation, requesting new pages as needed

    assumes the given search has a composite aggregation of the given name
    with a single value source of the given name

    updates the search in-place for subsequent pages
    '''
    if after is not None:
        search.aggs[composite_agg_name].after = {composite_source_name: after}
    while True:
        _page_response = search.execute(ignore_cache=True)  # reused search object has the previous page cached
        try:
            _agg_result = _page_response.aggregations[composite_agg_name]
        except KeyError:
            return  # no data; all done
        for _bucket in _agg_result.buckets:
            _key = _bucket.key.to_dict()
            assert set(_key.keys()) == {composite_source_name}, f'expected only one key ("{composite_source_name}") in {_bucket.key}'
            yield _key[composite_source_name]
        # update the search for the next page
        try:
            _next_after = _agg_result.after_key
        except AttributeError:
            return  # all done
        else:
            search.aggs[composite_agg_name].after = _next_after
