from datetime import timedelta

from django.test import TestCase
from elasticsearch_metrics.tests.util import RealElasticTestCase

from osf.metrics.events import SSRMetricsEvent
from osf.metrics.monthly_reports import MonthlyAngularSSRMetricsReport
from osf.metrics.reporters.angular_ssr_metrics import AngularSSRMetricsReporter
from osf.metrics.utils import YearMonth
from ._testutils import list_monthly_reports


class TestAngularSSRMetricsReporter(RealElasticTestCase, TestCase):
    @property
    def ym_empty(self) -> YearMonth:
        return YearMonth(2026, 7)

    @property
    def ym_with_data(self) -> YearMonth:
        return YearMonth(2026, 8)

    def test_no_data(self):
        _reports = list_monthly_reports(AngularSSRMetricsReporter(self.ym_empty))
        assert len(_reports) == 1
        _report = _reports[0]
        assert isinstance(_report, MonthlyAngularSSRMetricsReport)
        assert _report.bot_render_count == 0
        assert _report.bot_render_success_count == 0
        assert _report.bot_render_success_rate == 0.0
        assert _report.avg_ttfb_ms == 0.0
        assert _report.complete_render_count == 0
        assert _report.complete_render_rate == 0.0
        assert list(_report.content_type_breakdown) == []
        assert list(_report.user_agent_breakdown) == []

    def test_reporter(self):
        _month_start = self.ym_with_data.month_start()
        _record_ssr_event(
            timestamp=_month_start,
            url='/project1/', status=200, ttfb=100,
            isBot=True, isComplete=True, contentType='project', userAgent='Googlebot',
        )
        _record_ssr_event(
            timestamp=_month_start + timedelta(minutes=1),
            url='/preprint1/', status=200, ttfb=200,
            isBot=True, isComplete=True, contentType='preprint', userAgent='Googlebot',
        )
        _record_ssr_event(
            timestamp=_month_start + timedelta(minutes=2),
            url='/project2/', status=200, ttfb=300,
            isBot=True, isComplete=False, contentType='project', userAgent='Applebot',
        )
        _record_ssr_event(
            timestamp=_month_start + timedelta(minutes=3),
            url='/broken/', status=500, ttfb=50,
            isBot=True, isComplete=False, contentType=None, userAgent='Googlebot',
        )
        # not a bot - should be excluded from reporter data
        _record_ssr_event(
            timestamp=_month_start + timedelta(minutes=4),
            url='/project1/', status=200, ttfb=10,
            isBot=False, isComplete=True, contentType='project', userAgent='FakeGooglebot',
        )
        SSRMetricsEvent.refresh()

        _reports = list_monthly_reports(AngularSSRMetricsReporter(self.ym_with_data))
        assert len(_reports) == 1
        _report = _reports[0]
        assert isinstance(_report, MonthlyAngularSSRMetricsReport)
        assert _report.report_yearmonth == self.ym_with_data
        assert _report.bot_render_count == 4
        assert _report.bot_render_success_count == 3
        assert _report.bot_render_success_rate == 0.75
        assert _report.avg_ttfb_ms == 162.5
        assert _report.complete_render_count == 2
        assert _report.complete_render_rate == 0.5

        _content_types = {_c.content_type: _c.count for _c in _report.content_type_breakdown}
        assert _content_types == {'project': 2, 'preprint': 1, '(unspecified)': 1}

        _user_agents = {_u.user_agent: _u.count for _u in _report.user_agent_breakdown}
        assert _user_agents == {'Googlebot': 3, 'Applebot': 1}


def _record_ssr_event(**kwargs):
    SSRMetricsEvent.record(**kwargs)
