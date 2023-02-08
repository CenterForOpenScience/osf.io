from osf.metrics.counted_usage import CountedUsage
from osf.metrics.reports import MonthlyUseReport
from ._base import MonthlyReporter


class MonthlyUseReporter(MonthlyReporter):
    def report(self, report_yearmonth):
        start = report_yearmonth.target_month()
        end = report_yearmonth.next_month()
        search = (
            CountedUsage.search()
            .filter('range', timestamp={'gte': start, 'lte': end})
            [:0]  # just the aggregations, no hits
        )
        search.aggs.metric('total_session_hours', 'cardinality', field='session_id')
        result = search.execute()
        total_session_hours = result.aggs.total_session_hours.value
        month_timedelta = (end - start)
        month_hours = (24 * month_timedelta.days) + int(month_timedelta.seconds / (60 * 60))
        average_sessions_per_hour = total_session_hours / month_hours
        report = MonthlyUseReport(
            report_yearmonth=report_yearmonth,
            total_session_hours=total_session_hours,
            average_sessions_per_hour=average_sessions_per_hour,
        )
        return [report]
