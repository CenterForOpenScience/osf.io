from nose.tools import *
from webtest_plus import TestApp

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
    def setUp(self):
        super(TestViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

        self.app = TestApp(app)

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


