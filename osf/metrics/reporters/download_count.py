from osf.models import PageCounter
from osf.metrics.reports import DownloadCountReport
from osf.metrics.es8_metrics import DailyDownloadCountReportEs8
from osf.metrics.utils import cycle_coverage_date
from ._base import DailyReporter


class DownloadCountReporter(DailyReporter):
    def report(self, date):
        download_count = int(PageCounter.get_all_downloads_on_date(date) or 0)
        reports = []
        report_es8 = DailyDownloadCountReportEs8(
            cycle_coverage=cycle_coverage_date(date),
            daily_file_downloads=download_count,
        )
        reports.append(report_es8)
        report = DownloadCountReport(
            daily_file_downloads=report_es8.daily_file_downloads,
            report_date=date,
        )
        reports.append(report)
        return reports
