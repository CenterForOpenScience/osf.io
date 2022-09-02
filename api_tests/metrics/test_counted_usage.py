from datetime import datetime, timezone

import pytest
from unittest import mock

from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    # NodeFactory,
    # RegistrationFactory,
    # FileFactory,
    # UserFactory,
)


COUNTED_USAGE_URL = '/_/metrics/events/counted_usage/'

def counted_usage_payload(**attributes):
    return {
        'data': {
            'type': 'counted-usage',
            'attributes': attributes,
        },
    }


def assert_saved_with(mock_save, *, expected_doc_id=None, expected_attrs):
    assert mock_save.call_count == 1
    args, kwargs = mock_save.call_args
    actual_instance = args[0]
    if expected_doc_id is not None:
        assert actual_instance.meta.id == expected_doc_id
    actual_attrs = actual_instance.to_dict()
    for attr_name, expected_value in expected_attrs.items():
        actual_value = actual_attrs.get(attr_name, None)
        assert actual_value == expected_value, repr(actual_value)


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

    @pytest.fixture(autouse=True)
    def mock_now(self):
        timestamp = datetime(1981, 1, 1, 0, 1, 31, tzinfo=timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=timestamp):
            yield timestamp

    @pytest.fixture
    def mock_save(self):
        with mock.patch('elasticsearch_dsl.Document.save', autospec=True) as mock_save:
            yield mock_save

    @pytest.fixture()
    def user(self):
        with mock.patch('osf.models.base.generate_guid', return_value='guidy'):
            return AuthUserFactory()

    def test_by_client_session_id(self, app, mock_save, user):
        payload = counted_usage_payload(
            client_session_id='hello',
            item_guid='zyxwv',
            action_labels=['view', 'api'],
            pageview_info={'page_url': 'http://example.foo/blahblah/blee'},
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers, auth=user.auth)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|http://example.foo/blahblah/blee|5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34|1981-01-01|3').hexdigest()
            expected_doc_id='55fffffdc0d674d15a5e8763d14e4ae90f658fbfb6fbf94f88a5d24978f02e72',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_guid': 'zyxwv',
                # session_id: sha256(b'hello|1981-01-01').hexdigest()
                'session_id': '5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34',
                'action_labels': ['view', 'api'],
                'pageview_info': {
                    'page_url': 'http://example.foo/blahblah/blee',
                    'page_path': '/blahblah/blee',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_client_session_id_anon(self, app, mock_save):
        payload = counted_usage_payload(
            client_session_id='hello',
            item_guid='zyxwv',
            action_labels=['view', 'web'],
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
            # doc_id: sha256(b'http://example.foo/|http://example.foo/bliz/|5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34|1981-01-01|3').hexdigest()
            expected_doc_id='e559ffbc4bd3e3e69252d34c273f0e771ec89ee455ec9b60fbbadf3944e4af4e',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_guid': 'zyxwv',
                # session_id: sha256(b'hello|1981-01-01').hexdigest()
                'session_id': '5b7c8b0a740a5b23712258a9d1164d2af008df02a8e3d339f16ead1d19595b34',
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

    def test_by_user_auth(self, app, mock_save, user):
        payload = counted_usage_payload(
            item_guid='yxwvu',
            action_labels=['view', 'web'],
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
            # doc_id: sha256(b'http://example.foo/|http://osf.io/mst3k|ec768abb16c3411570af99b9d635c2c32d1ca31d1b25eec8ee73759e7242e74a|1981-01-01|3').hexdigest()
            expected_doc_id='743494d8a55079b91e202da1dbdfce5aea72e310c57a34b36df2c2af5ed4d362',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_guid': 'yxwvu',
                # session_id: sha256(b'guidy|1981-01-01|0').hexdigest()
                'session_id': 'ec768abb16c3411570af99b9d635c2c32d1ca31d1b25eec8ee73759e7242e74a',
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

    def test_by_useragent_header(self, app, mock_save):
        payload = counted_usage_payload(
            item_guid='yxwvu',
            action_labels=['view', 'api'],
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            # doc_id: sha256(b'http://example.foo/|yxwvu|97098dd3f7cd26053c0d0264d1c84eaeea8e08d2c55ca34017ffbe53c749ba5a|1981-01-01|3').hexdigest()
            expected_doc_id='a50ac1b2dc1c918cdea7be50b005117fdb6ee00ea069ca3aa4aaf03c0f905fa0',
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_guid': 'yxwvu',
                # session_id: sha256(b'localhost:80|haha|1981-01-01|0').hexdigest()
                'session_id': '97098dd3f7cd26053c0d0264d1c84eaeea8e08d2c55ca34017ffbe53c749ba5a',
                'action_labels': ['view', 'api'],
                'pageview_info': None,
            },
        )

    def test_provider_and_surrounding_guids(self, app, mock_save):
        preprint = PreprintFactory()

        payload = counted_usage_payload(
            item_guid=preprint._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            expected_attrs={
                'provider_id': preprint.provider._id,
                'surrounding_guids': None,
            },
        )

        mock_save.reset_mock()

        payload = counted_usage_payload(
            item_guid=preprint.primary_file.get_guid(create=True)._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload)
        assert resp.status_code == 201
        assert_saved_with(
            mock_save,
            expected_attrs={
                'item_guid': preprint.primary_file.get_guid()._id,
                'provider_id': preprint.primary_file.provider,
                'surrounding_guids': [preprint._id],
            },
        )

    def test_subregistration_file(self, app, mock_save):
        expected_elastic_countedusage = {
            'action_labels': [
                'web',
                'view'
            ],
            'item_guid': 'zcfv2',
            'item_public': True,
            'pageview_info': {
                'hour_of_day': 19,
                'page_path': '/zcfv2',
                'page_title': 'OSF',
                'page_url': 'http://localhost:5000/zcfv2/',
                'referer_domain': 'localhost:5000',
                'referer_url': 'http://localhost:5000/qxga7/files/osfstorage',
                'route_name': 'ember-osf-web.guid-file'
            },
            'platform_iri': 'http://localhost:5000/',
            'provider_id': 'osfstorage',
            'session_id': 'a62e53e28e603e1c621b49076f9bd9c68b355e1a254738a84111720d749de638',
            'surrounding_guids': [
                'qxga7',
                '4bs8c'
            ],
            'timestamp': '2022-09-02T19:50:49.740200+00:00',
        }

        payload = counted_usage_payload(
            item_guid='zcfv2',
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload)
