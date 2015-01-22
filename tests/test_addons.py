# -*- coding: utf-8 -*-

import webtest
import unittest
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory

import time

import furl
import itsdangerous

from framework.auth import signing
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


class SetEnvironMiddleware(object):

    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        environ.update(self.kwargs)
        return self.app(environ, start_response)


class TestAddonAuth(OsfTestCase):

    def setUp(self):
        super(TestAddonAuth, self).setUp()
        self.flask_app = SetEnvironMiddleware(self.app.app, REMOTE_ADDR='127.0.0.1')
        self.test_app = webtest.TestApp(self.flask_app)
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
            nid=self.node._id,
            provider=self.node_addon.config.short_name,
        )
        options.update(kwargs)
        return api_url_for('get_auth', **options)

    def test_auth_download(self):
        url = self.build_url()
        res = self.test_app.get(url)
        assert_equal(res.json['auth'], views.make_auth(self.user))
        assert_equal(res.json['credentials'], self.node_addon.serialize_waterbutler_credentials())
        assert_equal(res.json['settings'], self.node_addon.serialize_waterbutler_settings())
        expected_url = furl.furl(self.node.api_url_for('create_waterbutler_log', _absolute=True))
        observed_url = furl.furl(res.json['callback_url'])
        observed_url.port = expected_url.port
        assert_equal(expected_url, observed_url)

    def test_auth_missing_args(self):
        url = self.build_url(cookie=None)
        res = self.test_app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_auth_bad_cookie(self):
        url = self.build_url(cookie=self.cookie[::-1])
        res = self.test_app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_auth_missing_addon(self):
        url = self.build_url(provider='queenhub')
        res = self.test_app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_auth_bad_ip(self):
        flask_app = SetEnvironMiddleware(self.app.app, REMOTE_ADDR='192.168.1.1')
        test_app = webtest.TestApp(flask_app)
        url = self.build_url()
        res = test_app.get(url, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestAddonLogs(OsfTestCase):

    def setUp(self):
        super(TestAddonLogs, self).setUp()
        self.flask_app = SetEnvironMiddleware(self.app.app, REMOTE_ADDR='127.0.0.1')
        self.test_app = webtest.TestApp(self.flask_app)
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

    def build_payload(self, metadata, **kwargs):
        options = dict(
            auth={'id': self.user._id},
            action='create',
            provider=self.node_addon.config.short_name,
            metadata=metadata,
            time=time.time() + 1000,
        )
        options.update(kwargs)
        options = {
            key: value
            for key, value in options.iteritems()
            if value is not None
        }
        message, signature = signing.default_signer.sign_payload(options)
        return {
            'payload': message,
            'signature': signature,
        }

    def test_add_log(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path})
        nlogs = len(self.node.logs)
        self.test_app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs + 1)

    def test_add_log_missing_args(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, auth=None)
        nlogs = len(self.node.logs)
        res = self.test_app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs)

    def test_add_log_no_user(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, auth={'id': None})
        nlogs = len(self.node.logs)
        res = self.test_app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs)

    def test_add_log_no_addon(self):
        path = 'pizza'
        node = ProjectFactory(creator=self.user)
        url = node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path})
        nlogs = len(node.logs)
        res = self.test_app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.node.reload()
        assert_equal(len(node.logs), nlogs)

    def test_add_log_bad_action(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, action='dance')
        nlogs = len(self.node.logs)
        res = self.test_app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs)


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
