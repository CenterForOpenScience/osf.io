from osf.metrics.counted_usage import CountedUsage
from osf.metrics.reports import MonthlyRouteUseReport
from ._base import MonthlyReporter


class MonthlyRouteUseReporter(MonthlyReporter):
    def report(self, report_yearmonth):
        start = report_yearmonth.as_datetime()
        end = report_yearmonth.next().as_datetime()
        search = (
            CountedUsage.search()
            .filter('range', timestamp={'gte': start, 'lte': end})
            [:0]  # just the aggregations, no hits
        )
        route_agg = search.aggs.bucket(
            'by_route',
            'terms',
            field='pageview_info.route_name',
        )
        route_agg.metric(
            'total_sessions',
            'cardinality',
            field='session_id',
            precision_threshold=40000,  # maximum precision
        )

        result = search.execute()

        reports = []
        for route_bucket in result.aggs.by_route.buckets:
            report = MonthlyRouteUseReport(
                report_yearmonth=report_yearmonth,
                route_name=route_bucket.key,
                use_count=route_bucket.doc_count,
                sessionhour_count=route_bucket.total_sessions.value,
            )
            reports.append(report)
        return reports
