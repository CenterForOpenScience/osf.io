import pytest
import mock

from website.util import api_v2_url
from osf_tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory


def _get_application_reset_route(app):
    path = 'applications/{}/reset/'.format(app.client_id)
    return api_v2_url(path, base_route='/')


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestApplicationReset:

    @pytest.fixture()
    def user_app(self, user):
        return ApiOAuth2ApplicationFactory(owner=user)

    @pytest.fixture()
    def user_reset_url(self, user_app):
        return _get_application_reset_route(user_app)

    @pytest.fixture()
    def correct(self, user_app):
        return {
            'data': {
                'id': user_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_revokes_tokens_and_resets(self, mock_method, user_app):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        user_app.reset_secret(save=True)
        mock_method.assert_called()
        user_app.reload()
        assert old_secret != user_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_does_not_save_without_save_param(
            self, mock_method, user_app):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        user_app.reset_secret()
        user_app.reload()
        assert old_secret == user_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_url_revokes_tokens_and_resets(
            self, mock_method, app, user, user_app, user_reset_url, correct):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        res = app.post_json_api(user_reset_url, correct, auth=user.auth)
        assert res.status_code == 201
        mock_method.assert_called()
        user_app.reload()
        assert old_secret != user_app.client_secret

    @mock.patch('osf.models.ApiOAuth2Application.reset_secret')
    def test_other_user_cannot_reset(
            self, mock_method, app, user_app, user_reset_url, correct
    ):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        other_user = AuthUserFactory()
        res = app.post_json_api(
            user_reset_url, correct,
            auth=other_user.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

    @mock.patch('osf.models.ApiOAuth2Application.reset_secret')
    def test_unauth_user_cannot_reset(
            self, mock_method, app, user_app, user_reset_url, correct
    ):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        res = app.post_json_api(
            user_reset_url, correct,
            auth=None,
            expect_errors=True
        )
        assert res.status_code == 401
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret
