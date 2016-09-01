import mock

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, ProjectFactory


class TestUserRateThrottle(ApiTestCase):

    def setUp(self):
        super(TestUserRateThrottle, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}'.format(API_BASE)

    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_allow.call_count, 1)


class TestNonCookieAuthThrottle(ApiTestCase):

    def setUp(self):
        super(TestNonCookieAuthThrottle, self).setUp()
        self.url = '/{}'.format(API_BASE)

    @mock.patch('api.base.throttling.NonCookieAuthThrottle.allow_request')
    def test_cookie_throttle_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(mock_allow.call_count, 1)


class TestAddContributorEmailThrottle(ApiTestCase):

    def setUp(self):
        super(TestAddContributorEmailThrottle, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user)

        self.url = '/{}'.format(API_BASE)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

        self.data_user_two = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id,
                        }
                    }
                }
            }
        }

    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_allow_request_not_called(self, mock_allow):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(mock_allow.call_count, 0)

    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_allow_request_called(self, mock_allow):
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(mock_allow.call_count, 1)
