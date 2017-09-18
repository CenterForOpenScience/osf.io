import mock
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory, ProjectFactory


@pytest.mark.django_db
class TestDefaultThrottleClasses:

    @mock.patch('api.base.throttling.BaseThrottle.get_ident')
    def test_default_throttle_class_calls(self, mock_base, app):
        base_url = '/{}nodes/'.format(API_BASE)
        res = app.get(base_url)
        assert res.status_code == 200
        assert mock_base.call_count == 2


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRootThrottle:

    @pytest.fixture()
    def url(self):
        return '/{}'.format(API_BASE)

    @mock.patch('api.base.throttling.RootAnonThrottle.allow_request')
    def test_root_throttle_unauthenticated_request(self, mock_allow, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert mock_allow.call_count == 1

    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    def test_root_throttle_unauthenticated_request(
            self, mock_allow, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


@pytest.mark.django_db
class TestUserRateThrottle:

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    def test_user_rate_allow_request_called(self, mock_allow, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


@pytest.mark.django_db
class TestNonCookieAuthThrottle:

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @mock.patch('api.base.throttling.NonCookieAuthThrottle.allow_request')
    def test_cookie_throttle_rate_allow_request_called(
            self, mock_allow, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert mock_allow.call_count == 1


@pytest.mark.django_db
class TestAddContributorEmailThrottle:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url(self):
        return '/{}'.format(API_BASE)

    @pytest.fixture()
    def url_contrib_public_project(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def data_user_two(self, user_two):
        return {
            'data': {
                'type': 'contributors',
                'attributes': {
                        'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id,
                        }
                    }
                }
            }
        }

    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_allow_request_not_called(
            self, mock_allow, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert mock_allow.call_count == 0

    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_allow_request_called(
            self, mock_allow, app, url_contrib_public_project, user, data_user_two):
        res = app.post_json_api(
            url_contrib_public_project,
            data_user_two,
            auth=user.auth)
        assert res.status_code == 201
        assert mock_allow.call_count == 1

    @mock.patch('api.base.throttling.NonCookieAuthThrottle.allow_request')
    @mock.patch('rest_framework.throttling.UserRateThrottle.allow_request')
    @mock.patch('api.base.throttling.AddContributorThrottle.allow_request')
    def test_add_contrib_throttle_rate_and_default_rates_called(
            self, mock_contrib_allow, mock_user_allow, mock_anon_allow,
            app, url_contrib_public_project, user):

        res = app.get(url_contrib_public_project, auth=user.auth)
        assert res.status_code == 200
        assert mock_anon_allow.call_count == 1
        assert mock_user_allow.call_count == 1
        assert mock_contrib_allow.call_count == 1
