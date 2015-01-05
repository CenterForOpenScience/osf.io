# -*- coding: utf-8 -*-

import unittest
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory

import furl
import itsdangerous

from framework.auth.core import Auth
from framework.exceptions import HTTPError
from framework.sessions.model import Session

from website import settings
from website.util import api_url_for
from website.project import new_private_link
from website.addons.base import AddonConfig, AddonNodeSettingsBase, views
from website.addons.github.model import AddonGitHubOauthSettings


class TestAddonConfig(unittest.TestCase):

    def setUp(self):
        self.addon_config = AddonConfig(
            short_name='test', full_name='test', owners=['node'],
            added_to={'node': False}, categories=[],
            settings_model=AddonNodeSettingsBase,
        )

    def test_static_url_relative(self):
        url = self.addon_config._static_url('foo')
        assert_equal(
            url,
            '/static/addons/test/foo'
        )

    def test_deleted_defaults_to_false(self):
        class MyAddonSettings(AddonNodeSettingsBase):
            pass

        config = MyAddonSettings()
        assert_is(config.deleted, False)

    def test_static_url_absolute(self):
        url = self.addon_config._static_url('/foo')
        assert_equal(
            url,
            '/foo'
        )


class TestAddonAuth(OsfTestCase):

    def setUp(self):
        super(TestAddonAuth, self).setUp()
        self.user = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user)
        self.session = Session(data={'auth_user_id': self.user._id})
        self.session.save()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session._id)
        self.configure_addon()

    def configure_addon(self):
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')
        self.oauth_settings = AddonGitHubOauthSettings(github_user_id='john')
        self.oauth_settings.save()
        self.user_addon.oauth_settings = self.oauth_settings
        self.user_addon.oauth_access_token = 'secret'
        self.user_addon.save()
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.save()

    def build_url(self, **kwargs):
        options = dict(
            action='download',
            cookie=self.cookie,
            token='',
            nid=self.node._id,
            provider=self.node_addon.config.short_name,
        )
        options.update(kwargs)
        return api_url_for('get_auth', **options)

    def test_auth_download(self):
        url = self.build_url()
        res = self.app.get(url)
        assert_equal(res.json['auth'], views.make_auth(self.user))
        assert_equal(res.json['credentials'], self.node_addon.serialize_waterbutler_credentials())
        assert_equal(res.json['settings'], self.node_addon.serialize_waterbutler_settings())
        expected_url = furl.furl(self.node.api_url_for('create_waterbutler_log', _absolute=True))
        observed_url = furl.furl(res.json['callback_url'])
        observed_url.port = expected_url.port
        assert_equal(expected_url, observed_url)

    def test_auth_missing_args(self):
        url = self.build_url(cookie=None)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_auth_bad_cookie(self):
        url = self.build_url(cookie=self.cookie[::-1])
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_auth_missing_addon(self):
        url = self.build_url(provider='queenhub')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)


class TestCheckAuth(OsfTestCase):

    def setUp(self):
        super(TestCheckAuth, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_has_permission(self):
        res = views.check_access(self.node, self.user, 'upload')
        assert_true(res)

    def test_not_has_permission_read_public(self):
        self.node.is_public = True
        self.node.save()
        res = views.check_access(self.node, None, 'download')

    def test_not_has_permission_read_has_link(self):
        link = new_private_link('red-special', self.user, [self.node], anonymous=False)
        res = views.check_access(self.node, None, 'download', key=link.key)

    def test_not_has_permission_logged_in(self):
        user2 = AuthUserFactory()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.node, user2, 'download')
        assert_equal(exc_info.exception.code, 403)

    def test_not_has_permission_not_logged_in(self):
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.node, None, 'download')
        assert_equal(exc_info.exception.code, 401)
