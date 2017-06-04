import mock

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf_tests.factories import AuthUserFactory


class TestThrottling(ApiTestCase):

    def setUp(self):
        super(TestThrottling, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}test/throttle/'.format(API_BASE)

    def test_anon_rate_throttle(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 429)

    def test_user_rate_throttle(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 429)

    @mock.patch('api.base.throttling.TestUserRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_allow.call_count, 1)

    @mock.patch('api.base.throttling.TestAnonRateThrottle.allow_request')
    def test_anon_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(mock_allow.call_count, 1)

    def test_user_rate_throttle_with_throttle_token(self):
        headers = { 'X-THROTTLE-TOKEN': 'test-token'}
        res = self.app.get(self.url, auth=self.user.auth, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, headers=headers)
        assert_equal(res.status_code, 200)

    def test_anon_rate_throttle_with_throttle_token(self):
        headers = {'X-THROTTLE-TOKEN': 'test-token'}
        res = self.app.get(self.url, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, headers=headers)
        assert_equal(res.status_code, 200)

    def test_user_rate_throttle_with_incorrect_throttle_token(self):
        headers = {'X-THROTTLE-TOKEN': 'fake-token'}
        res = self.app.get(self.url, auth=self.user.auth, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 429)

    def test_anon_rate_throttle_with_incorrect_throttle_token(self):
        headers = {'X-THROTTLE-TOKEN': 'fake-token'}
        res = self.app.get(self.url, headers=headers)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, headers=headers, expect_errors=True)
        assert_equal(res.status_code, 429)
