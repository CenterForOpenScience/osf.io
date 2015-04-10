import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from website.app import init_app
from website.util import api_url_for

from framework.auth import Auth

from website.addons.twofactor.tests import _valid_code
from website.addons.twofactor.views import serialize_settings, serialize_urls

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
        user = AuthUserFactory()
        settings = serialize_settings(Auth(user))
        assert_false(settings['is_enabled'])
        assert_false(settings['is_confirmed'])
        assert_equal(settings['secret'], None)
        assert_equal(settings['drift'], None)

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

    def test_twofactor_settings_get_enabled(self):
        url = api_url_for('twofactor_settings_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['result'], serialize_settings(Auth(self.user)))

    def test_twofactor_settings_get_disabled(self):
        user = AuthUserFactory()
        url = api_url_for('twofactor_settings_get')
        res = self.app.get(url, auth=user.auth)        
        assert_equal(res.json['result'], serialize_settings(Auth(user)))

    def test_twofactor_enable_disabled(self):
        user = AuthUserFactory()
        url = api_url_for('twofactor_enable')
        res = self.app.post(url, {}, auth=user.auth)

        import ipdb; ipdb.set_trace()

    def test_twofactor_enable_enabled(self):
        pass
