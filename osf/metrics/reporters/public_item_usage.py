from __future__ import annotations
import datetime
import typing

from elasticsearch8 import dsl as esdsl

from osf.metadata.osf_gathering import OsfmapPartition
from osf.metrics.es8_metrics import (
    MonthlyPublicItemUsageReportEs8,
    OsfCountedUsageEvent,
)
from osf.metrics.utils import YearMonth, cycle_coverage_yearmonth
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
        _after_item_iri = continue_after['item_iri'] if continue_after else None
        for _item_iri in self._each_item_iri(_after_item_iri):
            yield {'item_iri': _item_iri}

    def report(self, **report_kwargs):
        _item_iri = report_kwargs['item_iri']
        try:
            return [self._build_report(_item_iri)]
        except _SkipItem:
            return []

    def followup_task(self, report):
        _last_month = YearMonth.from_date(datetime.date.today()).prior()
        if report.report_yearmonth == _last_month:
            from api.share.utils import task__update_share
            return task__update_share.signature(
                args=(report.item_osfids[0],),
                kwargs={
                    'is_backfill': True,
                    'osfmap_partition_name': OsfmapPartition.MONTHLY_SUPPLEMENT.name,
                },
                countdown=30,  # give index time to settle
            )

    def _each_item_iri(self, after_item_iri: str | None) -> typing.Iterator[str]:
        _search = self._base_usage_search()
        _search.aggs.bucket(
            'agg_item_iri',
            'composite',
            sources=[{'item_iri': {'terms': {'field': 'item_iri'}}}],
            size=_CHUNK_SIZE,
        )
        return _iter_composite_bucket_keys(_search, 'agg_item_iri', 'item_iri', after=after_item_iri)

    def _build_report(self, item_iri) -> MonthlyPublicItemUsageReportEs8:
        # get usage metrics from OsfCountedUsageEvent:
        #   - views of the item and its components and files (matching `within_iris`)
        #   - downloads for each item (matching `item_iri`)
        _search = self._build_usage_counts_search(item_iri)
        _response = _search.execute()
        _views_bucket = _response.aggregations.agg_by_label.buckets.views
        _downloads_bucket = _response.aggregations.agg_by_label.buckets.downloads
        _fields_agg = _response.aggregations.agg_for_terms
        _report = MonthlyPublicItemUsageReportEs8(
            report_yearmonth=self.yearmonth,
            item_iri=item_iri,
            item_osfids=_bucket_keys(_fields_agg.item_osfids.buckets),
            database_iris=_bucket_keys(_fields_agg.database_iris.buckets),
            platform_iris=_bucket_keys(_fields_agg.platform_iris.buckets),
            provider_ids=_bucket_keys(_fields_agg.provider_ids.buckets),
            item_types=_bucket_keys(_fields_agg.item_types.buckets),
            view_count=_views_bucket.doc_count,
            view_session_count=_views_bucket.agg_session_count.value,
            download_count=_downloads_bucket.doc_count,
            download_session_count=_downloads_bucket.agg_session_count.value,
            # same as non-cumulative counts, unless there's a prior report (added below)
            cumulative_view_count=_views_bucket.doc_count,
            cumulative_view_session_count=_views_bucket.agg_session_count.value,
            cumulative_download_count=_downloads_bucket.doc_count,
            cumulative_download_session_count=_downloads_bucket.agg_session_count.value,
        )
        _prior = self._prior_usage_report(item_iri)
        if _prior is not None:
            _report.cumulative_view_count += _prior.cumulative_view_count
            _report.cumulative_view_session_count += _prior.cumulative_view_session_count
            _report.cumulative_download_count += _prior.cumulative_download_count
            _report.cumulative_download_session_count += _prior.cumulative_download_session_count
        return _report

    def _base_usage_search(self):
        return (
            OsfCountedUsageEvent.search()
            .filter('term', item_public=True)
            .filter('range', timestamp={
                'lt': self.yearmonth.month_end(),
                'gte': self.yearmonth.month_start()
            })
            .extra(size=0)  # only aggregations, no hits
        )

    def _build_usage_counts_search(self, item_iri, cumulative: bool = False) -> tuple[int, int]:
        '''get usage counts for the given item_iri
        '''
        _search = self._base_usage_search().filter('term', within_iris=item_iri)

        # aggregation for counts by action label (views, downloads)
        _agg_by_label = esdsl.A('filters', filters={
            # bucket for views (including items within)
            'views': {'term': {'action_labels': OsfCountedUsageEvent.ActionLabel.VIEW.value}},
            # bucket for downloads (excluding items within)
            'downloads': {
                'bool': {
                    'filter': [
                        {'term': {'action_labels': OsfCountedUsageEvent.ActionLabel.DOWNLOAD.value}},
                        {'term': {'item_iri': item_iri}},
                    ],
                },
            },
        })
        # session count for each label bucket
        _agg_by_label.metric(
            'agg_session_count',
            'cardinality',
            field='sessionhour_id',
            precision_threshold=_MAX_CARDINALITY_PRECISION,
        )
        _search.aggs.bucket('agg_by_label', _agg_by_label)

        # aggregation for getting terms used on usage events directly on the item
        # (excluding items within) -- usually one value per field per item, but could be more
        _agg_for_terms = esdsl.A('filter', term={'item_iri': item_iri})
        _agg_for_terms.bucket('item_osfids', esdsl.A('terms', field='item_osfid'))
        _agg_for_terms.bucket('item_types', esdsl.A('terms', field='item_type'))
        _agg_for_terms.bucket('platform_iris', esdsl.A('terms', field='platform_iri'))
        _agg_for_terms.bucket('database_iris', esdsl.A('terms', field='database_iri'))
        _agg_for_terms.bucket('provider_ids', esdsl.A('terms', field='provider_id'))
        _search.aggs.bucket('agg_for_terms', _agg_for_terms)

        return _search

    def _prior_usage_report(self, item_iri):
        _search = (
            MonthlyPublicItemUsageReportEs8.search()
            .filter('term', item_iri=item_iri)
            .filter('range', cycle_coverage={
                'lt': cycle_coverage_yearmonth(self.yearmonth),
            })
            .sort('-cycle_coverage')  # most recent first
        )
        _response = _search[0].execute()
        return _response[0] if _response else None


def _bucket_keys(buckets):
    return [_bucket['key'] for _bucket in buckets]


def _iter_composite_bucket_keys(
    search: esdsl.Search,
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
