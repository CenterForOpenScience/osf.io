from elasticsearch_metrics.imps.elastic8 import CyclicRecord

from osf.metrics.reporters._base import MonthlyReporter


def list_monthly_reports(reporter: MonthlyReporter) -> list[CyclicRecord]:
    _each_reports_list = (
        reporter.report(**_kwargs)
        for _kwargs in reporter.iter_report_kwargs()
    )
    return [
        _report
        for _reports_list in _each_reports_list
        for _report in _reports_list
    ]
