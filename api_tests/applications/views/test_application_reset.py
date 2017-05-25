import pytest
import mock

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url
from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory

def _get_application_reset_route(app):
    path = 'applications/{}/reset/'.format(app.client_id)
    return api_v2_url(path, base_route='/')

@pytest.mark.django_db
class TestApplicationReset:

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_one_app(self, user_one):
        return ApiOAuth2ApplicationFactory(owner=user_one)

    @pytest.fixture()
    def user_one_reset_url(self, user_one_app):
        return _get_application_reset_route(user_one_app)

    @pytest.fixture()
    def correct(self, user_one_app):
        return {
            'data': {
                'id': user_one_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_revokes_tokens_and_resets(self, mock_method, user_one_app):
        mock_method.return_value(True)
        old_secret = user_one_app.client_secret
        user_one_app.reset_secret(save=True)
        mock_method.assert_called()
        user_one_app.reload()
        assert old_secret != user_one_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_does_not_save_without_save_param(self, mock_method, user_one_app):
        mock_method.return_value(True)
        old_secret = user_one_app.client_secret
        user_one_app.reset_secret()
        user_one_app.reload()
        assert old_secret == user_one_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_url_revokes_tokens_and_resets(self, mock_method, app, user_one, user_one_app, user_one_reset_url, correct):
        mock_method.return_value(True)
        old_secret = user_one_app.client_secret
        res = app.post_json_api(user_one_reset_url, correct, auth=user_one.auth)
        assert res.status_code == 201
        mock_method.assert_called()
        user_one_app.reload()
        assert old_secret != user_one_app.client_secret

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_other_user_cannot_reset(self, mock_method, app, user_one_app, user_one_reset_url, correct):
        mock_method.return_value(True)
        old_secret = user_one_app.client_secret
        user2 = AuthUserFactory()
        res = app.post_json_api(user_one_reset_url, correct, auth=user2.auth, expect_errors=True)
        assert res.status_code == 403
        mock_method.assert_not_called()
        user_one_app.reload()
        assert old_secret == user_one_app.client_secret

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_unauth_user_cannot_reset(self, mock_method, app, user_one_app, user_one_reset_url, correct):
        mock_method.return_value(True)
        old_secret = user_one_app.client_secret
        res = app.post_json_api(user_one_reset_url, correct, auth=None, expect_errors=True)
        assert res.status_code == 401
        mock_method.assert_not_called()
        user_one_app.reload()
        assert old_secret == user_one_app.client_secret
