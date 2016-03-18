import mock

from nose.tools import *  # flake8: noqa

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory

def _get_application_reset_route(app):
    path = "applications/{}/reset/".format(app.client_id)
    return api_v2_url(path, base_route='/')

class TestApplicationReset(ApiTestCase):
    def setUp(self):
        super(TestApplicationReset, self).setUp()

        self.user1 = AuthUserFactory()

        self.user1_app = ApiOAuth2ApplicationFactory(owner=self.user1)
        self.user1_reset_url = _get_application_reset_route(self.user1_app)

        self.correct = {
            'data': {
                'id': self.user1_app.client_id,
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
        old_secret = self.user1_app.client_secret
        self.user1_app.reset_secret(save=True)
        mock_method.assert_called()
        self.user1_app.reload()
        assert_not_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_does_not_save_without_save_param(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        self.user1_app.reset_secret()
        self.user1_app.reload()
        assert_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_url_revokes_tokens_and_resets(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        res = self.app.post_json_api(self.user1_reset_url, self.correct, auth=self.user1.auth)
        assert_equal(res.status_code, 201)
        mock_method.assert_called()
        self.user1_app.reload()
        assert_not_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_other_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        self.user2 = AuthUserFactory()
        res = self.app.post_json_api(self.user1_reset_url, self.correct, auth=self.user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        mock_method.assert_not_called()
        self.user1_app.reload()
        assert_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_unauth_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        res = self.app.post_json_api(self.user1_reset_url, self.correct, auth=None, expect_errors=True)
        assert_equal(res.status_code, 401)
        mock_method.assert_not_called()
        self.user1_app.reload()
        assert_equal(old_secret, self.user1_app.client_secret)

    def tearDown(self):
        super(TestApplicationReset, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()
