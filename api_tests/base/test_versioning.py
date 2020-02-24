import pytest
from api.base.settings import REST_FRAMEWORK, LATEST_VERSIONS


valid_url_path_version = '2.0'
valid_header_version = '2.1'
valid_query_parameter_version = '2.2'

invalid_url_path_version = '1.0'
invalid_header_version = '1.0.1'
invalid_query_parameter_version = '1.1'

invalid_url_path_version_url = '/v1/'
valid_url_path_version_url = '/v2/'

invalid_query_parameter_version_url = '/v2/?version={}'.format(
    invalid_query_parameter_version
)
valid_query_parameter_version_url = '/v2/?version={}'.format(
    valid_query_parameter_version
)


@pytest.mark.django_db
class TestBaseVersioning:

    def test_url_path_version(self, app):
        res = app.get(valid_url_path_version_url)
        assert res.status_code == 200
        assert res.json['meta']['version'] == valid_url_path_version

    def test_header_version(self, app):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(valid_header_version)
        }
        res = app.get(valid_url_path_version_url, headers=headers)
        assert res.status_code == 200
        assert res.json['meta']['version'] == valid_header_version

    def test_query_param_version(self, app):
        res = app.get(valid_query_parameter_version_url)
        assert res.status_code == 200
        assert res.json['meta']['version'] == valid_query_parameter_version

    def test_url_path_version_not_in_allowed_versions(self, app):
        res = app.get(invalid_url_path_version_url, expect_errors=True)
        assert res.status_code == 404

    def test_header_version_not_in_allowed_versions(self, app):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(invalid_header_version)
        }
        res = app.get(
            valid_url_path_version_url,
            headers=headers,
            expect_errors=True
        )
        assert res.status_code == 406
        assert res.json['errors'][0]['detail'] == 'Invalid version in "Accept" header.'

    def test_query_param_version_not_in_allowed_versions(self, app):
        res = app.get(invalid_query_parameter_version_url, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Invalid version in query parameter.'

    def test_header_version_and_query_parameter_version_match(self, app):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(valid_header_version)
        }
        url = '/v2/?version={}'.format(valid_header_version)
        res = app.get(url, headers=headers)
        assert res.status_code == 200
        assert res.json['meta']['version'] == valid_header_version

    def test_header_version_and_query_parameter_version_mismatch(self, app):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(valid_header_version)}
        url = '/v2/?version={}'.format(valid_query_parameter_version)
        res = app.get(url, headers=headers, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Version {} specified in "Accept" header does not match version {} specified in query parameter'.format(
            valid_header_version, valid_query_parameter_version
        )

    def test_header_version_bad_format(self, app):
        headers = {
            'accept': 'application/vnd.api+json;version=not_at_all_a_version'
        }
        res = app.get(
            valid_url_path_version_url,
            headers=headers,
            expect_errors=True
        )
        assert res.status_code == 406
        assert res.json['errors'][0]['detail'] == 'Invalid version in "Accept" header.'

    def test_query_version_bad_format(self, app):
        url = '/v2/?version=not_at_all_a_version'
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Invalid version in query parameter.'

    def test_query_version_latest_v2(self, app):
        url = '/v2/?version=latest'
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['meta']['version'] == LATEST_VERSIONS[2]

    def test_header_version_latest(self, app):
        headers = {'accept': 'application/vnd.api+json;version=latest'}
        res = app.get(valid_url_path_version_url, headers=headers)
        assert res.status_code == 200
        assert res.json['meta']['version'] == LATEST_VERSIONS[2]

    def test_browsable_api_defaults_to_latest(self, app):
        url = '/v2/?format=api'
        res = app.get(url)
        assert res.status_code == 200
        assert '&quot;version&quot;: &quot;{}&quot'.format(
            LATEST_VERSIONS[2]
        ) in res.body.decode()

    def test_browsable_api_query_version(self, app):
        url = '/v2/?format=api&version=2.5'
        res = app.get(url)
        assert res.status_code == 200
        assert b'&quot;version&quot;: &quot;2.5&quot' in res.body

    def test_json_defaults_to_default(self, app):
        url = '/v2/?format=json'
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['meta']['version'] == REST_FRAMEWORK['DEFAULT_VERSION']

    def test_json_api_defaults_to_default(self, app):
        url = '/v2/?format=jsonapi'
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['meta']['version'] == REST_FRAMEWORK['DEFAULT_VERSION']
