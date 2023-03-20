from osf.metrics.counted_usage import CountedUsage
from osf.metrics.reports import MonthlySessionhoursReport
from ._base import MonthlyReporter


class MonthlySessionhoursReporter(MonthlyReporter):
    def report(self, report_yearmonth):
        start = report_yearmonth.as_datetime()
        end = report_yearmonth.next().as_datetime()
        search = (
            CountedUsage.search()
            .filter('range', timestamp={'gte': start, 'lte': end})
            [:0]  # just the aggregations, no hits
        )
        search.aggs.metric(
            'total_sessionhour_count',
            'cardinality',
            field='session_id',
            precision_threshold=40000,  # maximum precision
        )
        result = search.execute()
        total_sessionhour_count = result.aggs.total_sessionhour_count.value
        month_timedelta = (end - start)
        month_hours = (24 * month_timedelta.days) + int(month_timedelta.seconds / (60 * 60))
        average_sessions_per_hour = total_sessionhour_count / month_hours
        report = MonthlySessionhoursReport(
            report_yearmonth=report_yearmonth,
            total_sessionhour_count=total_sessionhour_count,
            average_sessions_per_hour=average_sessions_per_hour,
        )
        return [report]
