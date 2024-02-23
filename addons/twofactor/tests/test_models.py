import unittest
from future.moves.urllib.parse import urlparse, urljoin, parse_qs

import pytest
from addons.twofactor.tests.utils import _valid_code
from osf_tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCallbacks(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.user = UserFactory()
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

    def test_add_to_user(self):
        self.assertEqual(self.user_settings.totp_drift, 0)
        self.assertIsNotNone(self.user_settings.totp_secret)
        self.assertFalse(self.user_settings.is_confirmed)

    def test_remove_from_unconfirmed_user(self):
        # drift defaults to 0. Change it so we can test it was changed back.
        self.user_settings.totp_drift = 1
        self.user_settings.save()

        self.user.delete_addon('twofactor')
        self.user_settings.reload()

        self.assertEqual(self.user_settings.totp_drift, 0)
        self.assertIsNone(self.user_settings.totp_secret)
        self.assertFalse(self.user_settings.is_confirmed)

    def test_remove_from_confirmed_user(self):
        # drift defaults to 0. Change it so we can test it was changed back.
        self.user_settings.totp_drift = 1
        self.user_settings.is_confirmed = True
        self.user_settings.save()

        self.user.delete_addon('twofactor')
        self.user_settings.reload()

        self.assertEqual(self.user_settings.totp_drift, 0)
        self.assertIsNone(self.user_settings.totp_secret)
        self.assertFalse(self.user_settings.is_confirmed)


class TestUserSettingsModel(unittest.TestCase):
    TOTP_SECRET = 'b8f85986068f8079aa9d'
    TOTP_SECRET_B32 = 'XD4FTBQGR6AHTKU5'

    def setUp(self):
        super().setUp()

        self.user = UserFactory()
        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

        self.user_settings.totp_secret = self.TOTP_SECRET
        self.user_settings.save()

    def tearDown(self):
        super().tearDown()
        self.user.__class__.delete(self.user)

    def test_b32(self):
        self.assertEqual(self.user_settings.totp_secret_b32, self.TOTP_SECRET_B32)

    def test_otpauth_url(self):
        url = urlparse(self.user_settings.otpauth_url)

        self.assertEqual(url.scheme, 'otpauth')
        self.assertEqual(url.netloc, 'totp')
        self.assertEqual(url.path, f'/OSF:{self.user.username}')
        self.assertEqual(
            parse_qs(url.query),
            {'secret': [self.TOTP_SECRET_B32]}
        )

    def test_json(self):
        # url = 'otpauth://totp/OSF:{}?secret=' + self.TOTP_SECRET_B32

        settings = self.user_settings.to_json(user=None)
        self.assertEqual(
            settings,
            {
                'is_enabled': True,
                'addon_full_name': 'Two-factor Authentication',
                'addon_short_name': 'twofactor',
                'drift': 0,
                'is_confirmed': False,
                'nodes': [],
                'secret': self.TOTP_SECRET_B32,
                'has_auth': False,
            }
        )

    def test_verify_valid_code(self):
        self.assertTrue(
            self.user_settings.verify_code(_valid_code(self.TOTP_SECRET))
        )

    def test_verify_valid_core_drift(self):
        # use a code from 30 seconds in the future
        self.assertTrue(
            self.user_settings.verify_code(
                _valid_code(self.TOTP_SECRET, drift=1)
            )
        )

        # make sure drift is updated.
        self.assertEqual(self.user_settings.totp_drift, 1)

        # use a code from 60 seconds in the future
        self.assertTrue(
            self.user_settings.verify_code(
                _valid_code(self.TOTP_SECRET, drift=2)
            )
        )

        # make sure drift is updated.
        self.assertEqual(self.user_settings.totp_drift, 2)

        # use the current code (which is now 2 periods away from the drift)
        self.assertFalse(
            self.user_settings.verify_code(_valid_code(self.TOTP_SECRET))
        )
