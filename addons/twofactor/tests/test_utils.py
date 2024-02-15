import pytest
from framework.auth import Auth
from nose.tools import assert_equal, assert_false, assert_in, assert_true
from osf_tests.factories import UserFactory
from tests.base import OsfTestCase
from addons.twofactor.utils import serialize_settings, serialize_urls

pytestmark = pytest.mark.django_db


class TestUtils(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user_addon = self.user.get_or_add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

    def test_serialize_urls_enabled(self):
        urls = serialize_urls(self.user_addon)
        for key in ['enable', 'disable', 'settings', 'otpauth']:
            assert_in(key, urls)
        assert_equal(urls['otpauth'], self.user_addon.otpauth_url)

    def test_serialize_urls_disabled(self):
        urls = serialize_urls(None)
        for key in ['enable', 'disable', 'settings', 'otpauth']:
            assert_in(key, urls)
        assert_equal(urls['otpauth'], '')

    def test_serialize_settings_enabled_and_unconfirmed(self):
        settings = serialize_settings(Auth(self.user))
        assert_true(settings['is_enabled'])
        assert_false(settings['is_confirmed'])
        assert_equal(settings['secret'], self.user_addon.totp_secret_b32)
        assert_equal(settings['drift'], self.user_addon.totp_drift)

    def test_serialize_settings_enabled_and_confirmed(self):
        self.user_addon.is_confirmed = True
        self.user_addon.save()
        settings = serialize_settings(Auth(self.user))
        assert_true(settings['is_enabled'])
        assert_true(settings['is_confirmed'])
        assert_equal(settings['secret'], self.user_addon.totp_secret_b32)
        assert_equal(settings['drift'], self.user_addon.totp_drift)

    def test_serialize_settings_disabled(self):
        user = UserFactory()
        settings = serialize_settings(Auth(user))
        assert_false(settings['is_enabled'])
        assert_false(settings['is_confirmed'])
        assert_equal(settings['secret'], None)
        assert_equal(settings['drift'], None)
