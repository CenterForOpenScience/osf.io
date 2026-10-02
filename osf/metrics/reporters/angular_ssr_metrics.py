from osf.metrics.events import SSRMetricsEvent
from osf.metrics.monthly_reports import (
    MonthlyAngularSSRMetricsReport,
    SSRContentTypeCount,
    SSRUserAgentCount,
)
from ._base import MonthlyReporter

MAX_CONTENT_LENGTH = 25


class AngularSSRMetricsReporter(MonthlyReporter):
    report_name = 'Angular SSR Metrics'

    def report(self):
        _search = self._base_search()
        _search.aggs.metric('agg_avg_ttfb', 'avg', field='ttfb')
        _search.aggs.bucket('agg_by_outcome', 'filters', filters={
            'total': {'match_all': {}},
            'success': {'range': {'status': {'gte': 200, 'lt': 300}}},
            'complete': {'term': {'isComplete': True}},
        })
        _search.aggs.bucket(
            'agg_content_type', 'terms',
            field='contentType', size=MAX_CONTENT_LENGTH, missing='(unspecified)',
        )
        _search.aggs.bucket('agg_user_agent', 'terms', field='userAgent', size=MAX_CONTENT_LENGTH)
        _response = _search.execute()
        if not _response.aggregations:
            yield MonthlyAngularSSRMetricsReport(
                report_yearmonth=self.yearmonth,
                bot_render_count=0,
                bot_render_success_count=0,
                bot_render_success_rate=0.0,
                avg_ttfb_ms=0.0,
                complete_render_count=0,
                complete_render_rate=0.0,
                content_type_breakdown=[],
                user_agent_breakdown=[],
            )
            return

        _outcome = _response.aggregations.agg_by_outcome.buckets
        _render_count = _outcome.total.doc_count
        _success_count = _outcome.success.doc_count
        _complete_count = _outcome.complete.doc_count

        yield MonthlyAngularSSRMetricsReport(
            report_yearmonth=self.yearmonth,
            bot_render_count=_render_count,
            bot_render_success_count=_success_count,
            bot_render_success_rate=_safe_rate(_success_count, _render_count),
            avg_ttfb_ms=_response.aggregations.agg_avg_ttfb.value or 0.0,
            complete_render_count=_complete_count,
            complete_render_rate=_safe_rate(_complete_count, _render_count),
            content_type_breakdown=[
                SSRContentTypeCount(content_type=_bucket.key, count=_bucket.doc_count)
                for _bucket in _response.aggregations.agg_content_type.buckets
            ],
            user_agent_breakdown=[
                SSRUserAgentCount(user_agent=_bucket.key, count=_bucket.doc_count)
                for _bucket in _response.aggregations.agg_user_agent.buckets
            ],
        )

    def _base_search(self):
        return (
            SSRMetricsEvent.search_timeseries_range(
                self.yearmonth.month_start(),
                self.yearmonth.month_end(),
            )
            .filter('term', isBot=True)
            .extra(size=0)  # only aggregations, no hits
        )


def _safe_rate(success: int, total: int) -> float:
    return (success / total) if total else 0.0
