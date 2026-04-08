from datetime import datetime

from osf.metrics.es8_metrics import (
    Es8DownloadCountReport,
    Es8UserSummaryReport,
    OsfCountedUsageRecord,
    PageviewInfo
)


class TestEs8Metrics:
    def test_import_all_reports(self):
        assert True

    def test_instantiate_of_reports(self):
        download_report = Es8DownloadCountReport()
        assert hasattr(download_report, 'daily_file_downloads')
        assert download_report.daily_file_downloads is None

        user_report = Es8UserSummaryReport()
        assert hasattr(user_report, 'active')
        assert user_report.active is None

    def test_nested_pageview(self):
        usage = OsfCountedUsageRecord(
            pageview_info={
                "page_url": "https://example.com",
                "referer_url": "https://google.com",
            }
        )
        assert usage.pageview_info is not None

    def test_pageview_info_autofill(self):
        obj = PageviewInfo(
            page_url="https://example.com/path/test",
            referer_url="https://google.com",
            timestamp=datetime(2024, 1, 1, 15, 0),
        )

        assert obj.page_path == "/path/test"
        assert obj.referer_domain == "google.com"
        assert obj.hour_of_day == 15
