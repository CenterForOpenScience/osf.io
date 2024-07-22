from unittest import mock

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory

class TestDefaultThrottleClasses(ApiTestCase):

    @mock.patch('api.base.throttling.BaseThrottle.get_ident')
    def test_default_throttle_class_calls(self, mock_base):
        '''
        check DEFAULT_THROTTLE_CLASSES for throttles being tested.
        '''
        base_url = f'/{API_BASE}nodes/'
        res = self.app.get(base_url)
        assert res.status_code == 200
        assert mock_base.call_count == 4  # UserRateThrottle get_ident is called twice due to cache key


class TestRootThrottle(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.url = f'/{API_BASE}'
        self.user = AuthUserFactory()

    @mock.patch('api.base.throttling.RootAnonThrottle.allow_request')
    def test_root_throttle_unauthenticated_request(self, mock_allow):
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert mock_allow.call_count == 1

    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    def test_root_throttle_authenticated_request(self, mock_allow):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


class TestUserRateThrottle(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.url = f'/{API_BASE}nodes/'

    @mock.patch('api.base.throttling.UserRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


class TestBurstRateThrottle(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.url = f'/{API_BASE}nodes/'

    @mock.patch('api.base.throttling.BurstRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


class TestNonCookieAuthThrottle(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.url = f'/{API_BASE}nodes/'

    @mock.patch('api.base.throttling.NonCookieAuthThrottle.allow_request')
    def test_cookie_throttle_rate_allow_request_called(self, mock_allow):
        '''
        check DEFAULT_THROTTLE_CLASSES for throttles being tested, NonCookieAuthThrottle is called twice as it's used by
        two sibling classes of throttle.
        '''
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert mock_allow.call_count == 2


class TestAddContributorEmailThrottle(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user)

        self.url = f'/{API_BASE}'
        self.public_url = '/{}nodes/{}/contributors/'.format(
            API_BASE, self.public_project._id)

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
    def test_add_contrib_throttle_rate_allow_request_not_called(
            self, mock_allow):
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert mock_allow.call_count == 0

    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_allow_request_called(self, mock_allow):
        res = self.app.post_json_api(
            self.public_url,
            self.data_user_two,
            auth=self.user.auth)
        assert res.status_code == 201
        assert mock_allow.call_count == 1

    @mock.patch('api.base.throttling.NonCookieAuthThrottle.allow_request')
    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_and_default_rates_called(
            self, mock_contrib_allow, mock_user_allow, mock_anon_allow):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert res.status_code == 200
        # NonCookieAuthThrottle is called twice as it's used by two sibling classes of throttle.
        assert mock_anon_allow.call_count == 2
        assert mock_user_allow.call_count == 1
        assert mock_contrib_allow.call_count == 1
