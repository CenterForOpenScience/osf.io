from datetime import datetime

from elasticsearch_metrics.tests.util import djelme_test_backends
import pytest

from osf.metrics.es8_metrics import (
    PageviewInfo,
    DownloadCountReportEs8,
    OsfCountedUsageRecord,
)


class TestEs8Metrics:
    """smoke tests to check that djelme records can be saved and searched"""
    @pytest.fixture(autouse=True)
    def _real_elastic(self):
        with djelme_test_backends():
            yield

    def test_nested_pageview_autofill(self):
        usage = OsfCountedUsageRecord.record(
            timestamp=datetime(2024, 1, 1, 15, 0),
            sessionhour_id='blah',
            database_iri='https://osf.example/provider',
            item_iri='https://osf.example/itemm',
            item_osfid='itemm',
            item_public=True,
            item_type='https://osf.example/Preprint',
            platform_iri='https://osf.example',
            user_is_authenticated=False,
            pageview_info=PageviewInfo(
                page_url="https://example.com/path/test",
                referer_url="https://google.com",
                route_name='foo.bar',
                page_title='title title',
            ),
        )
        assert usage.pageview_info.page_path == "/path/test"
        assert usage.pageview_info.referer_domain == "google.com"
        assert usage.pageview_info.hour_of_day == 15

    def test_save_report(self):
        _saved = DownloadCountReportEs8.record(
            cycle_coverage="2026.1.1",
            daily_file_downloads=17,
        )
        DownloadCountReportEs8.refresh_timeseries_indexes()
        _response = DownloadCountReportEs8.search().execute()
        (_fetched,) = _response
        assert _fetched.meta.id == _saved.meta.id
        assert _fetched.cycle_coverage == '2026.1.1'
        assert _fetched.daily_file_downloads == 17
