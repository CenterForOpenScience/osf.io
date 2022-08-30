from datetime import datetime, timezone

import pytest
from unittest import mock

from osf_tests.factories import AuthUserFactory


COUNTED_USAGE_URL = '/_/metrics/events/counted_usage/'

def counted_usage_payload(**attributes):
    return {
        'data': {
            'type': 'counted-usage',
            'attributes': attributes,
        },
    }


def assert_saved_with(mock_save, *, expected_doc_id, expected_attrs):
    assert mock_save.call_count == 1
    args, kwargs = mock_save.call_args
    actual_instance = args[0]
    actual_attrs = actual_instance.to_dict()
    for attr_name, expected_value in expected_attrs.items():
        actual_value = actual_attrs.get(attr_name, None)
        assert actual_value == expected_value, repr(actual_value)
    assert actual_instance.meta.id == expected_doc_id


@pytest.mark.django_db
class TestRestrictions:
    def test_http_method(self, app):
        resp = app.put(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.get(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.patch(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.delete(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('attrs', [
        {},
        {'item_guid': 'foo', 'action_labels': []},
        {'action_labels': []},
        {'pageview_info': {'page_url': 'http://example.foo/blahblah/blee'}},
    ])
    def test_required_attributes(self, app, attrs):
        payload = counted_usage_payload(**attrs)
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, expect_errors=True)
        assert resp.status_code == 400


@pytest.mark.django_db
class TestComputedFields:
    @pytest.fixture(autouse=True)
    def mock_domain(self):
        domain = 'http://example.foo/'
        with mock.patch('api.metrics.serializers.website_settings.DOMAIN', new=domain):
            yield domain

    @pytest.fixture
    def mock_save(self):
        with mock.patch('elasticsearch_dsl.Document.save', autospec=True) as mock_save:
            yield mock_save

    @pytest.fixture
    def now(self):
        timestamp = datetime(1981, 1, 1, 0, 1, 31, tzinfo=timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=timestamp):
            yield timestamp

    @pytest.fixture()
    def user(self):
        with mock.patch('osf.models.base.generate_guid', return_value='guidy'):
            return AuthUserFactory()

    def test_by_client_session_id(self, app, mock_save, now, user):
        payload = counted_usage_payload(
            client_session_id='hello',
            item_guid='zyxwv',
            action_labels=['view', 'api'],
            item_public=True,
            pageview_info={'page_url': 'http://example.foo/blahblah/blee'},
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers, auth=user.auth)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|osf|http://example.foo/blahblah/blee|5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34|1981-01-01|3').hexdigest()
            expected_doc_id='8a92beb12e160eb73cbe26fa4db91e231c1f051f5d262ff822a326cf4cd824b8',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'provider_id': 'osf',
                'item_guid': 'zyxwv',
                # session_id: sha256(b'hello|1981-01-01').hexdigest()
                'session_id': '5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34',
                'item_public': True,
                'action_labels': ['view', 'api'],
                'pageview_info': {
                    'page_url': 'http://example.foo/blahblah/blee',
                    'page_path': '/blahblah/blee',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_client_session_id_anon(self, app, mock_save, now):
        payload = counted_usage_payload(
            client_session_id='hello',
            item_guid='zyxwv',
            action_labels=['view', 'web'],
            item_public=True,
            pageview_info={
                'page_url': 'http://example.foo/bliz/',
                'referer_url': 'http://elsewhere.baz/index.php',
            },
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|osf|http://example.foo/bliz/|5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34|1981-01-01|3').hexdigest()
            expected_doc_id='7ed7936bba3be6a49c45680fd7be134cf8df7241c6b526c021d66f7134fcd728',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'provider_id': 'osf',
                'item_guid': 'zyxwv',
                # session_id: sha256(b'hello|1981-01-01').hexdigest()
                'session_id': '5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34',
                'item_public': True,
                'action_labels': ['view', 'web'],
                'pageview_info': {
                    'page_url': 'http://example.foo/bliz/',
                    'page_path': '/bliz',
                    'referer_url': 'http://elsewhere.baz/index.php',
                    'referer_domain': 'elsewhere.baz',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_user_auth(self, app, mock_save, now, user):
        payload = counted_usage_payload(
            item_guid='yxwvu',
            action_labels=['view', 'web'],
            item_public=False,
            pageview_info={
                'page_url': 'http://osf.io/mst3k',
                'referer_url': 'http://osf.io/registries/discover',
            },
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers, auth=user.auth)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|osf|http://osf.io/mst3k|ec768abb16c3411570af99b9d635c2c32d1ca31d1b25eec8ee73759e7242e74a|1981-01-01|3').hexdigest()
            expected_doc_id='f692855557be9f6be99f94339d925aede713ee1798d9692285bf9434e8639e43',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'provider_id': 'osf',
                'item_guid': 'yxwvu',
                # session_id: sha256(b'guidy|1981-01-01|0').hexdigest()
                'session_id': 'ec768abb16c3411570af99b9d635c2c32d1ca31d1b25eec8ee73759e7242e74a',
                'item_public': False,
                'action_labels': ['view', 'web'],
                'pageview_info': {
                    'page_url': 'http://osf.io/mst3k',
                    'page_path': '/mst3k',
                    'referer_url': 'http://osf.io/registries/discover',
                    'referer_domain': 'osf.io',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_useragent_header(self, app, mock_save, now):
        payload = counted_usage_payload(
            item_guid='yxwvu',
            action_labels=['view', 'api'],
            item_public=False,
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|osf|yxwvu|97098dd3f7cd26053c0d0264d1c84eaeea8e08d2c55ca34017ffbe53c749ba5a|1981-01-01|3').hexdigest()
            expected_doc_id='92dd6ec64045abb294958bebe523c68c5f8589ca44bbdfba5272ef299e7286a9',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'provider_id': 'osf',
                'item_guid': 'yxwvu',
                # session_id: sha256(b'localhost:80|haha|1981-01-01|0').hexdigest()
                'session_id': '97098dd3f7cd26053c0d0264d1c84eaeea8e08d2c55ca34017ffbe53c749ba5a',
                'item_public': False,
                'action_labels': ['view', 'api'],
                'pageview_info': None,
            },
        )
