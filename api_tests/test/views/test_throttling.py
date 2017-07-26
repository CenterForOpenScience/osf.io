import mock
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory

@pytest.mark.django_db
class TestThrottling:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self):
        return '/{}test/throttle/'.format(API_BASE)

    def test_user_rate_throttle(self, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 429

    @mock.patch('api.base.throttling.TestUserRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1

    @mock.patch('api.base.throttling.TestAnonRateThrottle.allow_request')
    def test_anon_rate_allow_request_called(self, mock_allow, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert mock_allow.call_count == 1

    def test_anon_rate_throttle(self, app, url):
        res = app.get(url)
        assert res.status_code == 200
        res = app.get(url, expect_errors=True)
        assert res.status_code == 429

    def test_user_rate_throttle_with_throttle_token(self, app, url, user):
        headers = { 'X-THROTTLE-TOKEN': 'test-token'}
        res = app.get(url, auth=user.auth, headers=headers)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, headers=headers)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, headers=headers)
        assert res.status_code == 200

    def test_anon_rate_throttle_with_throttle_token(self, app, url):
        headers = {'X-THROTTLE-TOKEN': 'test-token'}
        res = app.get(url, headers=headers)
        assert res.status_code == 200
        res = app.get(url, headers=headers)
        assert res.status_code == 200

    def test_user_rate_throttle_with_incorrect_throttle_token(self, app, url, user):
        headers = {'X-THROTTLE-TOKEN': 'fake-token'}
        res = app.get(url, auth=user.auth, headers=headers)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, headers=headers)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, headers=headers, expect_errors=True)
        assert res.status_code == 429

    def test_anon_rate_throttle_with_incorrect_throttle_token(self, app, url):
        headers = {'X-THROTTLE-TOKEN': 'fake-token'}
        res = app.get(url, headers=headers)
        assert res.status_code == 200
        res = app.get(url, headers=headers, expect_errors=True)
        assert res.status_code == 429
