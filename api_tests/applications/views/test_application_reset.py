import pytest
import mock

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url
from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory

def _get_application_reset_route(app):
    path = "applications/{}/reset/".format(app.client_id)
    return api_v2_url(path, base_route='/')

@pytest.mark.django_db
class TestApplicationReset(object):

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user_one = AuthUserFactory()

        self.user_one_app = ApiOAuth2ApplicationFactory(owner=self.user_one)
        self.user_one_reset_url = _get_application_reset_route(self.user_one_app)

        self.correct = {
            'data': {
                'id': self.user_one_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_revokes_tokens_and_resets(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user_one_app.client_secret
        self.user_one_app.reset_secret(save=True)
        mock_method.assert_called()
        self.user_one_app.reload()
        assert old_secret != self.user_one_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_does_not_save_without_save_param(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user_one_app.client_secret
        self.user_one_app.reset_secret()
        self.user_one_app.reload()
        assert old_secret == self.user_one_app.client_secret

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_url_revokes_tokens_and_resets(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user_one_app.client_secret
        res = self.app.post_json_api(self.user_one_reset_url, self.correct, auth=self.user_one.auth)
        assert res.status_code == 201
        mock_method.assert_called()
        self.user_one_app.reload()
        assert old_secret != self.user_one_app.client_secret

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_other_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user_one_app.client_secret
        self.user2 = AuthUserFactory()
        res = self.app.post_json_api(self.user_one_reset_url, self.correct, auth=self.user2.auth, expect_errors=True)
        assert res.status_code == 403
        mock_method.assert_not_called()
        self.user_one_app.reload()
        assert old_secret == self.user_one_app.client_secret

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_unauth_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user_one_app.client_secret
        res = self.app.post_json_api(self.user_one_reset_url, self.correct, auth=None, expect_errors=True)
        assert res.status_code == 401
        mock_method.assert_not_called()
        self.user_one_app.reload()
        assert old_secret == self.user_one_app.client_secret
