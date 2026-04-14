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
        download_report = Es8DownloadCountReport(cycle_coverage='2026.01.01')
        assert hasattr(download_report, 'daily_file_downloads')

        user_report = Es8UserSummaryReport(cycle_coverage='2026.01.01')
        assert hasattr(user_report, 'active')

    def test_nested_pageview(self):
        usage = OsfCountedUsageRecord(
            cycle_coverage='2026.01.01',
            pageview_info={
                'page_url': 'https://example.com',
                'referer_url': 'https://google.com',
            }
        )
        assert usage.pageview_info is not None

    def test_pageview_info_autofill(self):
        obj = PageviewInfo(
            cycle_coverage='2026.01.01',
            page_url='https://example.com/path/test',
            referer_url='https://google.com',
            timestamp=datetime(2024, 1, 1, 15, 0),
        )

        assert obj.page_path == '/path/test'
        assert obj.referer_domain == 'google.com'
        assert obj.hour_of_day == 15
