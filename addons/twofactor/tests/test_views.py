import pytest
from nose.tools import assert_equal, assert_false, assert_in, assert_true
from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from addons.twofactor.tests import _valid_code
from website.util import api_url_for

pytestmark = pytest.mark.django_db


class TestViews(OsfTestCase):
    def setUp(self):
        super(TestViews, self).setUp()
        self.user = AuthUserFactory()
        self.user_addon = self.user.get_or_add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

    def test_confirm_code(self):
        # Send a valid code to the API endpoint for the user settings.
        url = api_url_for('twofactor_settings_put')
        res = self.app.put_json(
            url,
            {'code': _valid_code(self.user_settings.totp_secret)},
            auth=self.user.auth
        )

        # reload the user settings object from the DB
        self.user_settings.reload()

        assert_true(self.user_settings.is_confirmed)
        assert_equal(res.status_code, 200)

    def test_confirm_code_failure(self):
        url = api_url_for('twofactor_settings_put')
        res = self.app.put_json(
            url,
            {'code': '0000000'},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)
        json = res.json
        assert_in('verification code', json['message_long'])

        # reload the user settings object from the DB
        self.user_settings.reload()

        assert_false(self.user_settings.is_confirmed)
