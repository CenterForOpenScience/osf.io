from osf.metrics.reporters._base import MonthlyReporter
from osf.metrics.reports import MonthlyReport


def list_monthly_reports(reporter: MonthlyReporter, *, flat=False) -> list[MonthlyReport]:
    _each_reports_list = (
        reporter.report(**_kwargs)
        for _kwargs in reporter.iter_report_kwargs()
    )
    return [
        _report
        for _reports_list in _each_reports_list
        for _report in _reports_list
        if isinstance(_report, MonthlyReport)  # TODO: update tests with es8
    ]
