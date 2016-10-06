from nose.tools import *    # flake8: noqa

from api.base import settings
from tests.base import ApiTestCase

# The versions below are specifically for testing purposes and do not reflect the actual versioning of the API.
# If changes are made to this list, or to DEFAULT_VERSION, please reflect those changes in:
# api/base/settings/local-travis.py so that travis tests will pass.
TESTING_ALLOWED_VERSIONS = (
    '2.0',
    '2.0.1',
    '2.1',
    '3.0',
    '3.0.1',
)

DEFAULT_VERSION = '2.0'


class VersioningTestCase(ApiTestCase):

    def setUp(self):
        super(VersioningTestCase, self).setUp()

        self.valid_url_path_version = '2.0'
        self.valid_header_version = '2.0.1'
        self.valid_query_parameter_version = '2.1'

        self.invalid_url_path_version = '1.0'
        self.invalid_header_version = '1.0.1'
        self.invalid_query_parameter_version = '1.1'

        self.valid_url_path_version_url = '/v2/'
        self.invalid_url_path_version_url = '/v1/'

        self.valid_query_parameter_version_url = '/v2/?version={}'.format(self.valid_query_parameter_version)
        self.invalid_query_parameter_version_url = '/v2/?version={}'.format(self.invalid_query_parameter_version)

        settings.REST_FRAMEWORK['ALLOWED_VERSIONS'] = TESTING_ALLOWED_VERSIONS
        settings.REST_FRAMEWORK['DEFAULT_VERSION'] = DEFAULT_VERSION


class TestBaseVersioning(VersioningTestCase):

    def setUp(self):
        super(TestBaseVersioning, self).setUp()

    def test_url_path_version(self):
        res = self.app.get(self.valid_url_path_version_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['version'], self.valid_url_path_version)

    def test_header_version(self):
        headers = {'accept': 'application/vnd.api+json;version={}'.format(self.valid_header_version)}
        res = self.app.get(self.valid_url_path_version_url, headers=headers)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['version'], self.valid_header_version)

    def test_query_param_version(self):
        res = self.app.get(self.valid_query_parameter_version_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['version'], self.valid_query_parameter_version)

    def test_url_path_version_not_in_allowed_versions(self):
        res = self.app.get(self.invalid_url_path_version_url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_header_version_not_in_allowed_versions(self):
        headers = {'accept': 'application/vnd.api+json;version={}'.format(self.invalid_header_version)}
        res = self.app.get(self.valid_url_path_version_url, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 406)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid version in "Accept" header.')

    def test_query_param_version_not_in_allowed_versions(self):
        res = self.app.get(self.invalid_query_parameter_version_url, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid version in query parameter.')

    def test_query_parameter_version_not_within_url_path_major_version(self):
        url = '/v2/?version=3.0.1'
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(
            res.json['errors'][0]['detail'],
            'Version {} specified in query parameter does not fall within URL path version {}'.format(
                '3.0.1',
                self.valid_url_path_version
            )
        )

    def test_header_version_not_within_url_path_major_version(self):
        headers = {'accept': 'application/vnd.api+json;version=3.0.1'}
        res = self.app.get(self.valid_url_path_version_url, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(
            res.json['errors'][0]['detail'],
            'Version {} specified in "Accept" header does not fall within URL path version {}'.format(
                    '3.0.1',
                    self.valid_url_path_version
            )
        )

    def test_header_version_and_query_parameter_version_match(self):
        headers = {'accept': 'application/vnd.api+json;version={}'.format(self.valid_header_version)}
        url = '/v2/?version={}'.format(self.valid_header_version)
        res = self.app.get(url, headers=headers)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['version'], self.valid_header_version)

    def test_header_version_and_query_parameter_version_mismatch(self):
        headers = {'accept': 'application/vnd.api+json;version={}'.format(self.valid_header_version)}
        url = '/v2/?version={}'.format(self.valid_query_parameter_version)
        res = self.app.get(url, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(
            res.json['errors'][0]['detail'],
            'Version {} specified in "Accept" header does not match version {} specified in query parameter'.format(
                self.valid_header_version,
                self.valid_query_parameter_version
            )
        )

    def test_header_version_bad_format(self):
        headers = {'accept': 'application/vnd.api+json;version=not_at_all_a_version'}
        res = self.app.get(self.valid_url_path_version_url, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 406)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid version in "Accept" header.')

    def test_query_version_bad_format(self):
        url = '/v2/?version=not_at_all_a_version'
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid version in query parameter.')
