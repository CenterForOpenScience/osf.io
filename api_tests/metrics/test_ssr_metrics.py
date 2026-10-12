from unittest import mock

import pytest

from osf_tests.factories import (
    AuthUserFactory,
)


SSR_METRICS_URL = '/_/metrics/events/ssr_metrics/'

def ssr_metrics_payload(**attributes):
    return {
        'data': {
            'type': 'ssr-metrics',
            'attributes': attributes,
        },
    }


@pytest.fixture
def mock_es8():
    with mock.patch('elasticsearch_metrics.imps.elastic8.TimeseriesRecord.check_djelme_setup'):
        with mock.patch('elasticsearch_metrics.imps.elastic8.BaseDjelmeRecord._get_connection') as _mock_get_connection:
            _mock_es8 = _mock_get_connection.return_value
            _mock_es8.index.return_value = {'result': {}}
            yield _mock_es8


@pytest.mark.django_db
class TestSSRMetricsView:

    def get_response(self, app, mock_es8, payload, expected_status_code, expected_call_count):
        user = AuthUserFactory()
        if expected_status_code >= 400:
            resp = app.post_json_api(SSR_METRICS_URL, payload, auth=user.auth, expect_errors=True)
        else:
            resp = app.post_json_api(SSR_METRICS_URL, payload, auth=user.auth)

        assert resp.status_code == expected_status_code
        assert mock_es8.index.call_count == expected_call_count
        return resp

    def test_incorrect_url_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url=3,
            status=200,
            ttfb=100,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'url' in resp.json['errors'][0]['source']['pointer']
        assert 'Enter a valid URL' in resp.json['errors'][0]['detail']

    def test_incorrect_url(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='random',
            status=200,
            ttfb=100,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert len(resp.json['errors']) == 1
        assert 'url' in resp.json['errors'][0]['source']['pointer']
        assert 'Enter a valid URL' in resp.json['errors'][0]['detail']

    def test_incorrect_status_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status='failed',
            ttfb=100,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'status' in resp.json['errors'][0]
        assert 'A valid integer is required' in resp.json['errors'][0]['status']

    def test_incorrect_status_before_range_value(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=99,
            ttfb=100,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'status' in resp.json['errors'][0]
        assert 'Ensure this value is greater than or equal to 100.' in resp.json['errors'][0]['status']

    def test_incorrect_status_after_range_value(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=600,
            ttfb=100,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'status' in resp.json['errors'][0]
        assert 'Ensure this value is less than or equal to 599.' in resp.json['errors'][0]['status']

    def test_incorrect_ttfb_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5.5,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'ttfb' in resp.json['errors'][0]['source']['pointer']
        assert 'A valid integer is required' in resp.json['errors'][0]['detail']

    def test_incorrect_ttfb(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=-5,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert len(resp.json['errors']) == 1
        assert 'ttfb' in resp.json['errors'][0]['source']['pointer']
        assert 'Ensure this value is greater than or equal to 0.' in resp.json['errors'][0]['detail']

    def test_incorrect_is_bot_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=4,
            is_bot='string',
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'is_bot' in resp.json['errors'][0]['source']['pointer']
        assert 'Must be a valid boolean.' in resp.json['errors'][0]['detail']

    def test_incorrect_is_bot(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=4,
            is_bot=None,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert len(resp.json['errors']) == 1
        assert 'is_bot' in resp.json['errors'][0]['source']['pointer']
        assert 'This field may not be null.' in resp.json['errors'][0]['detail']

    def test_incorrect_is_complete_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete='string',
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'is_complete' in resp.json['errors'][0]['source']['pointer']
        assert 'Must be a valid boolean.' in resp.json['errors'][0]['detail']

    def test_incorrect_is_complete(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete=None,
            user_agent='Mozilla/5.0',
            content_type=None
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert len(resp.json['errors']) == 1
        assert 'is_complete' in resp.json['errors'][0]['source']['pointer']
        assert 'This field may not be null.' in resp.json['errors'][0]['detail']

    def test_incorrect_content_type_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type=False
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'content_type' in resp.json['errors'][0]['source']['pointer']
        assert 'Not a valid string.' in resp.json['errors'][0]['detail']

    def test_incorrect_user_agent_type(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete=True,
            user_agent=True,
            content_type=3
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert 'user_agent' in resp.json['errors'][0]['source']['pointer']
        assert 'Not a valid string.' in resp.json['errors'][0]['detail']

    def test_incorrect_user_agent(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete=True,
            user_agent=None,
            content_type='some type'
        )
        resp = self.get_response(app, mock_es8, payload, expected_status_code=400, expected_call_count=0)
        assert len(resp.json['errors']) == 1
        assert 'user_agent' in resp.json['errors'][0]['source']['pointer']
        assert 'This field may not be null.' in resp.json['errors'][0]['detail']

    def test_valid_payload(self, app, mock_es8):
        payload = ssr_metrics_payload(
            url='http://example.com',
            status=200,
            ttfb=5,
            is_bot=False,
            is_complete=True,
            user_agent='Mozilla/5.0',
            content_type='some type'
        )
        self.get_response(app, mock_es8, payload, expected_status_code=201, expected_call_count=1)
        call = mock_es8.method_calls[0].kwargs['body']
        assert call['url'] == 'http://example.com'
        assert call['status'] == 200
        assert call['ttfb'] == 5
        assert call['isBot'] is False
        assert call['isComplete'] is True
        assert call['userAgent'] == 'Mozilla/5.0'
        assert call['contentType'] == 'some type'
        assert 'timestamp' in call
        assert 'timeseries_timeparts' in call
