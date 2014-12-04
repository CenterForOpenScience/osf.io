from urlparse import urlparse, parse_qs

import mock
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import UserFactory
from website.addons.twofactor.tests import _valid_code

class TestCallbacks(OsfTestCase):
    @mock.patch('website.addons.twofactor.models.push_status_message')
    def setUp(self, mocked):
        super(TestCallbacks, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')
        self.on_add_called = mocked.called

    def test_add_to_user(self):
        assert_equal(self.user_settings.totp_drift, 0)
        assert_is_not_none(self.user_settings.totp_secret)
        assert_false(self.user_settings.is_confirmed)
        assert_true(self.on_add_called)

    @mock.patch('website.addons.twofactor.models.push_status_message')
    def test_remove_from_unconfirmed_user(self, mocked):
        # drift defaults to 0. Change it so we can test it was changed back.
        self.user_settings.totp_drift = 1
        self.user_settings.save()

        self.user.delete_addon('twofactor')

        assert_equal(self.user_settings.totp_drift, 0)
        assert_is_none(self.user_settings.totp_secret)
        assert_false(self.user_settings.is_confirmed)
        assert_false(mocked.called)

    @mock.patch('website.addons.twofactor.models.push_status_message')
    def test_remove_from_confirmed_user(self, mocked):
        # drift defaults to 0. Change it so we can test it was changed back.
        self.user_settings.totp_drift = 1
        self.user_settings.is_confirmed = True
        self.user_settings.save()

        self.user.delete_addon('twofactor')

        assert_equal(self.user_settings.totp_drift, 0)
        assert_is_none(self.user_settings.totp_secret)
        assert_false(self.user_settings.is_confirmed)
        assert_true(mocked.called)


class TestUserSettingsModel(OsfTestCase):
    TOTP_SECRET = 'b8f85986068f8079aa9d'
    TOTP_SECRET_B32 = 'XD4FTBQGR6AHTKU5'

    @mock.patch('website.addons.twofactor.models.push_status_message')
    def setUp(self, mocked):
        super(TestUserSettingsModel, self).setUp()

        self.user = UserFactory(username='foo@bar.com')
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

        self.user_settings.totp_secret = self.TOTP_SECRET
        self.user_settings.save()

    def tearDown(self):
        super(TestUserSettingsModel, self).tearDown()
        self.user.__class__.remove_one(self.user)

    def test_b32(self):
        assert_equal(self.user_settings.totp_secret_b32, self.TOTP_SECRET_B32)

    def test_otpauth_url(self):
        url = urlparse(self.user_settings.otpauth_url)

        assert_equal(url.scheme, 'otpauth')
        assert_equal(url.netloc, 'totp')
        assert_equal(url.path, '/OSF:foo@bar.com')
        assert_equal(
            parse_qs(url.query),
            {'secret': [self.TOTP_SECRET_B32]}
        )

    def test_json(self):
        assert_equal(
            self.user_settings.to_json(user=None),
            {
                'addon_full_name': 'Two-factor Authentication',
                'addon_short_name': 'twofactor',
                'drift': 0,
                'is_confirmed': False,
                'nodes': [],
                'otpauth_url': 'otpauth://totp/OSF:foo@bar.com'
                               '?secret=' + self.TOTP_SECRET_B32,
                'secret': self.TOTP_SECRET_B32,
                'has_auth': False,
            }
        )

    def test_verify_valid_code(self):
        assert_true(
            self.user_settings.verify_code(_valid_code(self.TOTP_SECRET))
        )

    def test_verify_valid_core_drift(self):
        # use a code from 30 seconds in the future
        assert_true(
            self.user_settings.verify_code(
                _valid_code(self.TOTP_SECRET, drift=1)
            )
        )

        # make sure drift is updated.
        assert_equal(self.user_settings.totp_drift, 1)

        # use a code from 60 seconds in the future
        assert_true(
            self.user_settings.verify_code(
                _valid_code(self.TOTP_SECRET, drift=2)
            )
        )

        # make sure drift is updated.
        assert_equal(self.user_settings.totp_drift, 2)

        # use the current code (which is now 2 periods away from the drift)
        assert_false(
            self.user_settings.verify_code(_valid_code(self.TOTP_SECRET))
        )
