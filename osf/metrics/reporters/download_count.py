from osf.models import PageCounter
from osf.metrics.reports import DownloadCountReport
from ._base import DailyReporter


class DownloadCountReporter(DailyReporter):
    def report(self, date):
        download_count = int(PageCounter.get_all_downloads_on_date(date) or 0)
        return [
            DownloadCountReport(
                daily_file_downloads=download_count,
                report_date=date,
            ),
        ]

    def keen_events_from_report(self, report):
        event = {
            "files": {
                "total": report.daily_file_downloads,
            },
        }
        return {"download_count_summary": [event]}
