import mock
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from website.app import init_app
from website.addons.twofactor.tests import _valid_code

app = init_app(
    routes=True,
    set_backends=False,
    settings_module='website.settings',
)

class TestViews(OsfTestCase):
    @mock.patch('website.addons.twofactor.models.push_status_message')
    def setUp(self, mocked):
        super(TestViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

    def test_confirm_code(self):
        # Send a valid code to the API endpoint for the user settings.
        res = self.app.post_json(
            '/api/v1/settings/twofactor/',
            {'code': _valid_code(self.user_settings.totp_secret)},
            auth=self.user.auth
        )

        # reload the user settings object from the DB
        self.user_settings.reload()

        assert_true(self.user_settings.is_confirmed)
        assert_equal(res.status_code, 200)

    def test_confirm_code_failure(self):
        res = self.app.post_json(
            '/api/v1/settings/twofactor/',
            {'code': '000000'},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        json = res.json
        assert_in('verification code', json['message_long'])

        # reload the user settings object from the DB
        self.user_settings.reload()

        assert_false(self.user_settings.is_confirmed)
