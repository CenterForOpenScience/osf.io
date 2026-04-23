from osf.models import PageCounter
from osf.metrics.reports import DownloadCountReport
from ._base import DailyReporter
from osf.metrics.es8_metrics import DownloadCountReportEs8


class DownloadCountReporter(DailyReporter):
    def report(self, date):
        download_count = int(PageCounter.get_all_downloads_on_date(date) or 0)
        reports = []
        report_es8 = DownloadCountReportEs8(
            cycle_coverage=f"{date:%Y.%m.%d}",
            daily_file_downloads=download_count,
        )
        reports.append(report_es8)
        report = DownloadCountReport(
            daily_file_downloads=report_es8.daily_file_downloads,
            report_date=date,
        )
        reports.append(report)
        return reports
