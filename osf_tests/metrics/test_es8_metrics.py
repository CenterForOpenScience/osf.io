import datetime

from django.test import TestCase
from elasticsearch_metrics.tests.util import RealElasticTestCase

from osf.metrics.es8_metrics import DailyDownloadCountReportEs8
from osf.metrics.events import OsfCountedUsageEvent


class TestEs8Metrics(RealElasticTestCase, TestCase):
    """smoke tests to check that djelme records can be saved and searched"""

    def test_nested_pageview_autofill(self):
        usage = OsfCountedUsageEvent.record(
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, tzinfo=datetime.UTC),
            sessionhour_id='blah',
            database_iri='https://osf.example/provider',
            item_iri='https://osf.example/itemm',
            item_osfid='itemm',
            item_public=True,
            item_type='Preprint',
            platform_iri='https://osf.example',
            user_is_authenticated=False,
            pageview_info={
                'page_url': 'https://example.com/path/test',
                'referer_url': 'https://google.com',
                'route_name': 'foo.bar',
                'page_title': 'title title',
            },
        )
        assert usage.pageview_info.page_path == '/path/test'
        assert usage.pageview_info.referer_domain == 'google.com'
        assert usage.pageview_info.hour_of_day == 15
        assert usage.item_iri in usage.within_iris

    def test_nested_pageview_autofill_dict(self):
        usage = OsfCountedUsageEvent.record(
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, tzinfo=datetime.UTC),
            sessionhour_id='blah',
            database_iri='https://osf.example/provider',
            item_iri='https://osf.example/itemm',
            item_osfid='itemm',
            item_public=True,
            item_type='Preprint',
            platform_iri='https://osf.example',
            user_is_authenticated=False,
            pageview_info={
                'page_url': 'https://example.com/path/test',
                'referer_url': 'https://google.com',
                'route_name': 'foo.bar',
                'page_title': 'title title',
            },
        )
        assert usage.pageview_info.page_path == '/path/test'
        assert usage.pageview_info.referer_domain == 'google.com'
        assert usage.pageview_info.hour_of_day == 15
        assert usage.item_iri in usage.within_iris

    def test_none_pageview_nested_autofill(self):
        usage = OsfCountedUsageEvent.record(
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, tzinfo=datetime.UTC),
            sessionhour_id='blah',
            database_iri='https://osf.example/provider',
            item_iri='https://osf.example/itemm',
            item_osfid='itemm',
            item_public=True,
            item_type='Preprint',
            platform_iri='https://osf.example',
            user_is_authenticated=False,
        )
        assert not usage.pageview_info
        assert usage.item_iri in usage.within_iris

    def test_save_report(self):
        _saved = DailyDownloadCountReportEs8.record(
            cycle_coverage='2026.1.1',
            daily_file_downloads=17,
        )
        DailyDownloadCountReportEs8.refresh()
        _response = DailyDownloadCountReportEs8.search().execute()
        (_fetched,) = _response
        assert _fetched.meta.id == _saved.meta.id
        assert _fetched.cycle_coverage == '2026.1.1'
        assert _fetched.daily_file_downloads == 17
