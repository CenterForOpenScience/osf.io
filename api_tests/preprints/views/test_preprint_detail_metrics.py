import functools
from unittest import mock
import uuid

import pytest
from waffle.testutils import override_switch

from osf import features
from osf.models.base import osfid_iri
from osf.metrics.events import OsfCountedUsageEvent
from osf.metrics.monthly_reports import MonthlyPublicItemUsageReport
from osf.metrics.reporters.public_item_usage import PublicItemUsageReporter
from osf.metrics.utils import YearMonth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import PreprintFactory


@pytest.mark.django_db
class TestPreprintDetailWithMetrics:
    # enable the ELASTICSEARCH_METRICS switch for all tests
    @pytest.fixture(autouse=True)
    def enable_elasticsearch_metrics(self):
        with override_switch(features.ELASTICSEARCH_METRICS, active=True):
            yield

    @pytest.mark.parametrize('metric_name', ['downloads', 'views'])
    def test_preprint_detail_with_downloads(self, app, settings, metric_name):
        preprint = PreprintFactory()
        url = f'/{API_BASE}preprints/{preprint._id}/?metrics[{metric_name}]=total'

        with mock.patch('api.base.metrics.UsageMetricsViewMixin._get_usage_count') as mock_get_count:
            mock_get_count.return_value = 42
            res = app.get(url)

        assert res.status_code == 200
        data = res.json
        assert 'metrics' in data['meta']
        assert metric_name in data['meta']['metrics']
        assert data['meta']['metrics'][metric_name] == 42


@pytest.mark.django_db
@pytest.mark.osfmetrics_elastic_backends
class TestPreprintDetailWithElasticMetrics:

    @functools.cached_property
    def _preprint(self):
        return PreprintFactory()

    @functools.cached_property
    def _preprint_detail_url(self):
        return f'/{API_BASE}preprints/{self._preprint._id}/?metrics[views]=total&metrics[downloads]=total'

    @functools.cached_property
    def _this_month(self):
        return YearMonth.from_today()

    @functools.cached_property
    def _last_month(self):
        return self._this_month.prior()

    @functools.cached_property
    def _last_month_usage_events(self):
        # 2 views, 1 download
        _events = [
            self._save_view(self._last_month.month_start()),
            self._save_view(self._last_month.month_start()),
            self._save_download(self._last_month.month_start()),
        ]
        OsfCountedUsageEvent.refresh()
        return _events

    @functools.cached_property
    def _this_month_usage_events(self):
        # 3 views, 2 downloads
        _events = [
            self._save_view(self._this_month.month_start()),
            self._save_view(self._this_month.month_start()),
            self._save_view(self._this_month.month_start()),
            self._save_download(self._this_month.month_start()),
            self._save_download(self._this_month.month_start()),
        ]
        OsfCountedUsageEvent.refresh()
        return _events

    def _save_view(self, timestamp):
        return OsfCountedUsageEvent.record(
            timestamp=timestamp,
            item_osfid=self._preprint._id,
            action_labels=['view', 'web'],
            client_session_id=str(uuid.uuid4()),
        )

    def _save_download(self, timestamp):
        return OsfCountedUsageEvent.record(
            timestamp=timestamp,
            item_osfid=self._preprint._id,
            action_labels=['download'],
            client_session_id=str(uuid.uuid4()),
        )

    def _save_usage_report(self, yearmonth, **attr_overrides):
        _item_iri = osfid_iri(self._preprint._id)
        _reports = list(PublicItemUsageReporter(yearmonth).report(item_iri=_item_iri))
        for _report in _reports:
            for _attr_name, _attr_value in attr_overrides.items():
                setattr(_report, _attr_name, _attr_value)
            _report.save()
        return _reports

    def test_no_views_and_downloads(self, app):
        _res = app.get(self._preprint_detail_url)
        assert _res.status_code == 200
        _resp_metrics = _res.json['meta']['metrics']
        assert _resp_metrics['views'] == 0
        assert _resp_metrics['downloads'] == 0

    def test_with_usage_events_no_reports(self, app):
        self._this_month_usage_events
        self._last_month_usage_events
        _res = app.get(self._preprint_detail_url)
        assert _res.status_code == 200
        _resp_metrics = _res.json['meta']['metrics']
        assert _resp_metrics['views'] == 5
        assert _resp_metrics['downloads'] == 3

    def test_with_usage_events_and_reports(self, app):
        self._last_month_usage_events
        self._this_month_usage_events
        # last month's cumulative count should be used instead of querying all past events
        self._save_usage_report(
            self._last_month,
            cumulative_view_count=17,
            cumulative_download_count=13,
        )
        # this month's (premature) cumulative count should be ignored
        self._save_usage_report(
            self._this_month,
            cumulative_view_count=111,
            cumulative_download_count=333,
        )
        MonthlyPublicItemUsageReport.refresh()
        _res = app.get(self._preprint_detail_url)
        assert _res.status_code == 200
        _resp_metrics = _res.json['meta']['metrics']
        # 17 from last-month report, 3 from this-month events
        assert _resp_metrics['views'] == 17 + 3
        # 13 from last-month report, 2 from this-month events
        assert _resp_metrics['downloads'] == 13 + 2
