from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    import elasticsearch_dsl as edsl

from osf.metrics.counted_usage import (
    CountedAuthUsage,
    get_item_type,
    get_provider_id,
)
from osf.metrics.reports import PublicItemUsageReport
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

    def report(self):
        # use two composite aggregations in parallel to page thru every
        # public item viewed or downloaded this month, counting:
        # - views and downloads for each item (using `CountedAuthUsage.item_guid`)
        # - views for each item's components and files (using `CountedAuthUsage.surrounding_guids`)
        for _exact_bucket, _contained_views_bucket in _zip_composite_aggs(
            self._exact_item_search(), 'agg_osfid',
            self._contained_item_views_search(), 'agg_surrounding_osfid',
        ):
            try:
                _report = self._report_from_buckets(_exact_bucket, _contained_views_bucket)
                _report.view_session_count = self._get_view_session_count(_report.item_osfid)
                yield _report
            except _SkipItem:
                pass

    def _report_from_buckets(self, exact_bucket, contained_views_bucket):
        # either exact_bucket or contained_views_bucket may be None, but not both
        assert (exact_bucket is not None) or (contained_views_bucket is not None)
        _report = (
            self._init_report_from_exact_bucket(exact_bucket)
            if exact_bucket is not None
            else self._init_report_from_osfid(contained_views_bucket.key.osfid)
        )
        # view counts include views on contained items (components, files)
        if contained_views_bucket is not None:
            _report.view_count += contained_views_bucket.doc_count
        return _report

    def _init_report_from_exact_bucket(self, exact_bucket) -> PublicItemUsageReport:
        # in the (should-be common) case of an item that has been directly viewed in
        # this month, the stored metrics already have the data required
        _report = PublicItemUsageReport(
            item_osfid=exact_bucket.key.osfid,
            item_type=_agg_keys(exact_bucket.agg_item_type),
            provider_id=_agg_keys(exact_bucket.agg_provider_id),
            platform_iri=_agg_keys(exact_bucket.agg_platform_iri),
            # default counts to zero, will be updated if non-zero
            view_count=0,
            view_session_count=0,
            download_count=0,
            download_session_count=0,
        )
        for _actionbucket in exact_bucket.agg_action:
            if _actionbucket.key == CountedAuthUsage.ActionLabel.VIEW.value:
                _report.view_count = _actionbucket.doc_count
                # note: view_session_count computed separately to avoid double-counting
            elif _actionbucket.key == CountedAuthUsage.ActionLabel.DOWNLOAD.value:
                _report.download_count = _actionbucket.doc_count
                _report.download_session_count = _actionbucket.agg_session_count.value
        return _report

    def _init_report_from_osfid(self, osfid: str) -> PublicItemUsageReport:
        # for the (should-be unusual) case where the components/files contained by
        # an item have views in this month, but the item itself does not --
        # load necessary info via django models, instead
        _osfguid = osfdb.Guid.load(osfid)
        if _osfguid is None or not getattr(_osfguid.referent, 'is_public', False):
            raise _SkipItem
        return PublicItemUsageReport(
            item_osfid=osfid,
            item_type=[get_item_type(_osfguid.referent)],
            provider_id=[get_provider_id(_osfguid.referent)],
            platform_iri=[website_settings.DOMAIN],
            # default counts to zero, will be updated if non-zero
            view_count=0,
            view_session_count=0,
            download_count=0,
            download_session_count=0,
        )

    def _base_usage_search(self):
        return (
            CountedAuthUsage.search()
            .filter('term', item_public=True)
            .filter('range', timestamp={
                'gte': self.yearmonth.month_start(),
                'lt': self.yearmonth.month_end(),
            })
            .update_from_dict({'size': 0})  # only aggregations, no hits
        )

    def _exact_item_search(self) -> edsl.Search:
        '''aggregate views and downloads on each osfid (not including components/files)'''
        _search = self._base_usage_search()
        # the main agg: use a composite aggregation to page thru *every* item
        _agg_osfid = _search.aggs.bucket(
            'agg_osfid',
            'composite',
            sources=[{'osfid': {'terms': {'field': 'item_guid'}}}],
            size=_CHUNK_SIZE,
        )
        # nested agg: for each item, get platform_iri values
        _agg_osfid.bucket('agg_platform_iri', 'terms', field='platform_iri')
        # nested agg: for each item, get provider_id values
        _agg_osfid.bucket('agg_provider_id', 'terms', field='provider_id')
        # nested agg: for each item, get item_type values
        _agg_osfid.bucket('agg_item_type', 'terms', field='item_type')
        # nested agg: for each item, get view and download count
        _agg_action = _agg_osfid.bucket(
            'agg_action',
            'terms',
            field='action_labels',
            include=[
                CountedAuthUsage.ActionLabel.DOWNLOAD.value,
                CountedAuthUsage.ActionLabel.VIEW.value,
            ],
        )
        # nested nested agg: for each item-action pair, get a session count
        _agg_action.metric(
            'agg_session_count',
            'cardinality',
            field='session_id',
            precision_threshold=_MAX_CARDINALITY_PRECISION,
        )
        return _search

    def _contained_item_views_search(self) -> edsl.Search:
        '''aggregate views (but not downloads) on components and files contained within each osfid'''
        _search = (
            self._base_usage_search()
            .filter('term', action_labels=CountedAuthUsage.ActionLabel.VIEW.value)
        )
        # the main agg: use a composite aggregation to page thru *every* item
        _search.aggs.bucket(
            'agg_surrounding_osfid',
            'composite',
            sources=[{'osfid': {'terms': {'field': 'surrounding_guids'}}}],
            size=_CHUNK_SIZE,
        )
        return _search

    def _get_view_session_count(self, osfid: str):
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
                    {'term': {'item_guid': osfid}},
                    {'term': {'surrounding_guids': osfid}},
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
        return _response.aggregations.agg_session_count.value


###
# local helpers

def _agg_keys(bucket_agg_result) -> list:
    return [_bucket.key for _bucket in bucket_agg_result]


def _zip_composite_aggs(
    search_a: edsl.Search,
    composite_agg_name_a: str,
    search_b: edsl.Search,
    composite_agg_name_b: str,
):
    '''iterate thru two composite aggregations, yielding pairs of buckets matched by key

    the composite aggregations must have matching names in `sources` so their keys can be compared
    '''
    _iter_a = _iter_composite_buckets(search_a, composite_agg_name_a)
    _iter_b = _iter_composite_buckets(search_b, composite_agg_name_b)
    _next_a = next(_iter_a, None)
    _next_b = next(_iter_b, None)
    while True:
        if _next_a is None and _next_b is None:
            return  # both done
        elif _next_a is None or _next_b is None:
            # one is done but not the other -- no matching needed
            yield (_next_a, _next_b)
            _next_a = next(_iter_a, None)
            _next_b = next(_iter_b, None)
        elif _next_a.key == _next_b.key:
            # match -- yield and increment both
            yield (_next_a, _next_b)
            _next_a = next(_iter_a, None)
            _next_b = next(_iter_b, None)
        elif _orderable_key(_next_a) < _orderable_key(_next_b):
            # mismatch -- yield and increment a (but not b)
            yield (_next_a, None)
            _next_a = next(_iter_a, None)
        else:
            # mismatch -- yield and increment b (but not a)
            yield (None, _next_b)
            _next_b = next(_iter_b, None)


def _iter_composite_buckets(search: edsl.Search, composite_agg_name: str):
    '''iterate thru *all* buckets of a composite aggregation, requesting new pages as needed

    assumes the given search has a composite aggregation of the given name

    updates the search in-place for subsequent pages
    '''
    while True:
        _page_response = search.execute(ignore_cache=True)  # reused search object has the previous page cached
        try:
            _agg_result = _page_response.aggregations[composite_agg_name]
        except KeyError:
            return  # no data; all done
        yield from _agg_result.buckets
        # update the search for the next page
        try:
            _next_after = _agg_result.after_key
        except AttributeError:
            return  # all done
        else:
            search.aggs[composite_agg_name].after = _next_after


def _orderable_key(composite_bucket) -> list:
    return sorted(composite_bucket.key.to_dict().items())
