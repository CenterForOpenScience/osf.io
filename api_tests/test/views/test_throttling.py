from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory


class TestThrottling(ApiTestCase):

    def setUp(self):
        super(TestThrottling, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}test/throttle/'.format(API_BASE)

    def test_user_rate_throttle(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 429)

    def test_anon_rate_throttle(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 429)
