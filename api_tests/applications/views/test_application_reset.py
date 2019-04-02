import pytest
import mock

from website.util import api_v2_url
from api.base.settings import API_BASE
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
    def deprecated_user_reset_url(self, user_app):
        return _get_application_reset_route(user_app)

    @pytest.fixture()
    def application_detail_url(self, user_app):
        return '/{}applications/{}/?version=2.15'.format(API_BASE, user_app.client_id)

    @pytest.fixture()
    def deprecated_payload(self, user_app):
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

    @pytest.fixture()
    def payload(self, user_app):
        return {
            'data': {
                'id': user_app.client_id,
                'type': 'applications',
                'attributes': {
                    'client_secret': None
                }
            }
        }

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_revokes_tokens_and_resets(self, mock_method, user_app):
        mock_method.return_value(True)
        old_secret = user_app.client_secret
        user_app.reset_secret(save=True)
        mock_method.assert_called_with(user_app.client_id, old_secret)
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
    def test_deprecated_reset_url_revokes_tokens_and_resets(
            self, mock_method, app, user, user_app, deprecated_user_reset_url, deprecated_payload):
        mock_method.return_value(True)
        old_secret = user_app.client_secret

        res = app.post_json_api(deprecated_user_reset_url, deprecated_payload, auth=user.auth)
        assert res.status_code == 201
        assert 'This route is deprecated' in res.json['meta']['warnings'][0]
        mock_method.assert_called_with(user_app.client_id, old_secret)
        user_app.reload()
        assert old_secret != user_app.client_secret

    @mock.patch('osf.models.ApiOAuth2Application.reset_secret')
    def test_deprecated_reset_fails(
            self, mock_method, app, user_app, deprecated_user_reset_url, deprecated_payload):
        mock_method.return_value(True)
        old_secret = user_app.client_secret

        # non owner reset fails
        other_user = AuthUserFactory()
        res = app.post_json_api(
            deprecated_user_reset_url,
            deprecated_payload,
            auth=other_user.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # unauthorized user reset fails
        res = app.post_json_api(
            deprecated_user_reset_url,
            deprecated_payload,
            expect_errors=True
        )
        assert res.status_code == 401
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

    @mock.patch('osf.models.ApiOAuth2Application.reset_secret')
    def test_reset_fails(
            self, mock_method, app, user, user_app, application_detail_url, payload,
            deprecated_user_reset_url, deprecated_payload):
        mock_method.return_value(True)
        old_secret = user_app.client_secret

        # non owner reset fails
        other_user = AuthUserFactory()
        res = app.patch_json_api(
            application_detail_url,
            payload,
            auth=other_user.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # unauthorized user reset fails
        res = app.patch_json_api(
            application_detail_url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 401
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # reset with a new value does not reset
        payload['data']['attributes']['client_secret'] = 'Shouldnotbeabletodothis'
        res = app.patch_json_api(
            application_detail_url,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 200
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # reset with a truthy value does not reset
        payload['data']['attributes']['client_secret'] = 'True'
        res = app.patch_json_api(
            application_detail_url,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 200
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # test reset with no client secret does not reset
        del(payload['data']['attributes']['client_secret'])
        res = app.patch_json_api(
            application_detail_url,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 200
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

        # POST to old endpoint with newest version fails
        res = app.post_json_api(
            deprecated_user_reset_url + '?version=2.15',
            deprecated_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert 'This route has been deprecated' in res.json['errors'][0]['detail']
        mock_method.assert_not_called()
        user_app.reload()
        assert old_secret == user_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_client_secret(
            self, mock_revoke_application_tokens, app, user_app, user, application_detail_url, payload):
        mock_revoke_application_tokens.return_value = True
        old_secret = user_app.client_secret

        res = app.patch_json_api(
            application_detail_url,
            payload,
            auth=user.auth,
        )
        assert res.status_code == 200
        user_app.reload()
        assert mock_revoke_application_tokens.call_count == 1
        assert user_app.client_secret != old_secret
