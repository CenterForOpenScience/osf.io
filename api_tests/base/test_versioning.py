import pytest

from api.base import settings

# The versions below are specifically for testing purposes and do not reflect the actual versioning of the API.
# If changes are made to this list, or to DEFAULT_VERSION, please reflect those changes in:
# api/base/settings/local-travis.py so that travis tests will pass.
TESTING_ALLOWED_VERSIONS = (
    '2.0',
    '2.0.1',
    '2.1',
    '2.2',
    '3.0',
    '3.0.1',
)

DEFAULT_VERSION = '2.0'


@pytest.mark.django_db
class TestBaseVersioning:

    @pytest.fixture()
    def versions(self):

        settings.REST_FRAMEWORK['ALLOWED_VERSIONS'] = TESTING_ALLOWED_VERSIONS
        settings.REST_FRAMEWORK['DEFAULT_VERSION'] = DEFAULT_VERSION

        valid_query_parameter_version = '2.1'
        invalid_query_parameter_version = '1.1'

        versions = {
            'valid_url_path_version': '2.0',
            'valid_header_version': '2.0.1',
            'valid_query_parameter_version': valid_query_parameter_version,
            'invalid_url_path_version': '1.0',
            'invalid_header_version': '1.0.1',
            'invalid_query_parameter_version': invalid_query_parameter_version,
            'valid_url_path_version_url': '/v2/',
            'invalid_url_path_version_url': '/v1/',
            'valid_query_parameter_version_url': '/v2/?version={}'.format(valid_query_parameter_version),
            'invalid_query_parameter_version_url': '/v2/?version={}'.format(invalid_query_parameter_version),
            '_ALLOWED_VERSIONS': settings.REST_FRAMEWORK['ALLOWED_VERSIONS'],
            '_DEFAULT_VERSION': settings.REST_FRAMEWORK['DEFAULT_VERSION']}

        yield versions

        settings.REST_FRAMEWORK['ALLOWED_VERSIONS'] = versions['_ALLOWED_VERSIONS']
        settings.REST_FRAMEWORK['DEFAULT_VERSION'] = versions['_DEFAULT_VERSION']

    def test_url_path_version(self, app, versions):
        res = app.get(versions['valid_url_path_version_url'])
        assert res.status_code == 200
        assert res.json['meta']['version'] == versions['valid_url_path_version']

    def test_header_version(self, app, versions):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(versions['valid_header_version'])}
        res = app.get(versions['valid_url_path_version_url'], headers=headers)
        assert res.status_code == 200
        assert res.json['meta']['version'] == versions['valid_header_version']

    def test_query_param_version(self, app, versions):
        res = app.get(versions['valid_query_parameter_version_url'])
        assert res.status_code == 200
        assert res.json['meta']['version'] == versions['valid_query_parameter_version']

    def test_header_version_and_query_parameter_version_match(
            self, app, versions):
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(versions['valid_header_version'])}
        url = '/v2/?version={}'.format(versions['valid_header_version'])
        res = app.get(url, headers=headers)
        assert res.status_code == 200
        assert res.json['meta']['version'] == versions['valid_header_version']

    def test_non_mutational_base_versioning_tests(self, app, versions):

        # test_url_path_version_not_in_allowed_versions
        res = app.get(
            versions['invalid_url_path_version_url'],
            expect_errors=True)
        assert res.status_code == 404

        # test_header_version_not_in_allowed_versions
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(versions['invalid_header_version'])}
        res = app.get(
            versions['valid_url_path_version_url'],
            headers=headers,
            expect_errors=True)
        assert res.status_code == 406
        assert res.json['errors'][0]['detail'] == 'Invalid version in "Accept" header.'

        # test_query_param_version_not_in_allowed_versions
        res = app.get(
            versions['invalid_query_parameter_version_url'],
            expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Invalid version in query parameter.'

        # test_query_parameter_version_not_within_url_path_major_version
        url = '/v2/?version=3.0.1'
        res = app.get(url, expect_errors=True)
        assert res.status_code == 409
        assert (
            res.json['errors'][0]['detail'] ==
            'Version {} specified in query parameter does not fall within URL path version {}'.format(
                '3.0.1',
                versions['valid_url_path_version']
            ))

        # test_header_version_not_within_url_path_major_version
        headers = {'accept': 'application/vnd.api+json;version=3.0.1'}
        res = app.get(
            versions['valid_url_path_version_url'],
            headers=headers,
            expect_errors=True)
        assert res.status_code == 409
        assert (
            res.json['errors'][0]['detail'] ==
            'Version {} specified in "Accept" header does not fall within URL path version {}'.format(
                '3.0.1',
                versions['valid_url_path_version']
            ))

        # test_header_version_and_query_parameter_version_mismatch
        headers = {
            'accept': 'application/vnd.api+json;version={}'.format(versions['valid_header_version'])}
        url = '/v2/?version={}'.format(
            versions['valid_query_parameter_version'])
        res = app.get(url, headers=headers, expect_errors=True)
        assert res.status_code == 409
        assert (
            res.json['errors'][0]['detail'] ==
            'Version {} specified in "Accept" header does not match version {} specified in query parameter'.format(
                versions['valid_header_version'],
                versions['valid_query_parameter_version']
            ))

        # test_header_version_bad_format
        headers = {
            'accept': 'application/vnd.api+json;version=not_at_all_a_version'}
        res = app.get(
            versions['valid_url_path_version_url'],
            headers=headers,
            expect_errors=True)
        assert res.status_code == 406
        assert res.json['errors'][0]['detail'] == 'Invalid version in "Accept" header.'

        # test_query_version_bad_format
        url = '/v2/?version=not_at_all_a_version'
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Invalid version in query parameter.'
