from osf.models import PageCounter
from osf.metrics.reports import DailyDownloadCountReport
from ._base import DailyReporter


class DownloadCountReporter(DailyReporter):
    def report(self, date):
        download_count = int(PageCounter.get_all_downloads_on_date(date) or 0)
        yield DailyDownloadCountReport(
            report_date=date,
            daily_file_downloads=download_count,
        )
