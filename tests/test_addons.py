# -*- coding: utf-8 -*-

import time
import mock
import unittest
from nose.tools import *  # noqa

import webtest
import furl
import itsdangerous
from modularodm import storage

from framework.auth import signing
from framework.auth.core import Auth
from framework.exceptions import HTTPError
from framework.sessions.model import Session
from framework.mongo import set_up_storage

from website import settings
from website.util import api_url_for, rubeus
from website.addons.base import exceptions, GuidFile
from website.project import new_private_link
from website.project.utils import serialize_node
from website.addons.base import AddonConfig, AddonNodeSettingsBase, views
from website.addons.github.model import AddonGitHubOauthSettings
from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory


class DummyGuidFile(GuidFile):

    file_name = 'foo.md'
    name = 'bar.md'

    @property
    def provider(self):
        return 'dummy'

    @property
    def version_identifier(self):
        return 'versionidentifier'

    @property
    def unique_identifier(self):
        return 'dummyid'

    @property
    def waterbutler_path(self):
        return '/path/to/file/'

    def enrich(self):
        pass


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
        assert_equal(res.status_code, 401)

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


class OsfFileTestCase(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(OsfTestCase, cls).setUpClass()
        set_up_storage([DummyGuidFile], storage.MongoStorage)


class TestAddonFileViewHelpers(OsfFileTestCase):

    @mock.patch('website.addons.base.views.codecs.open')
    @mock.patch('website.addons.base.views.build_rendered_html')
    def test_get_or_start_starts(self, mock_render, mock_open):
        file_guid = DummyGuidFile(node=ProjectFactory())
        file_guid.save()
        mock_open.side_effect = IOError

        views.get_or_start_render(file_guid)
        mock_render.assert_called_once_with(
            file_guid.mfr_download_url,
            file_guid.mfr_cache_path,
            file_guid.mfr_temp_path,
            file_guid.public_download_url
        )

    # TODO: Use DummyGuidFile for the below tests instead of Mock
    @mock.patch('website.addons.base.views.codecs.open')
    @mock.patch('website.addons.base.views.build_rendered_html')
    def test_get_or_start_respects_start_render(self, mock_render, mock_open):
        file_guid = mock.Mock()
        mock_open.side_effect = IOError

        views.get_or_start_render(file_guid, start_render=False)

        assert_false(mock_render.called)

    @mock.patch('website.addons.base.views.codecs.open')
    @mock.patch('website.addons.base.views.build_rendered_html')
    def test_get_or_start_returns_found(self, mock_render, mock_open):
        file_guid = mock.Mock()
        mock_file = mock.Mock()

        mock_file.read.return_value = 'Look at me, I\'m mr meseeks'
        mock_open.return_value = mock_file

        assert_equal(
            'Look at me, I\'m mr meseeks',
            views.get_or_start_render(file_guid)
        )

        assert_false(mock_render.called)

    def test_get_or_start_returns_error(self):
        class MyException(exceptions.AddonEnrichmentError):

            def as_html(self):
                return 'wubalubadubdub'

        file_guid = mock.Mock()
        file_guid.enrich.side_effect = MyException()
        assert_equal(
            'wubalubadubdub',
            views.get_or_start_render(file_guid)
        )

    def test_key_error_raises_attr_error_for_name(self):
        class TestGuidFile(GuidFile):
            pass

        with assert_raises(AttributeError):
            TestGuidFile().name

    def test_getattrname_catches(self):
        class TestGuidFile(GuidFile):
            pass

        assert_equals(getattr(TestGuidFile(), 'name', 'foo'), 'foo')

    def test_getattrname(self):
        class TestGuidFile(GuidFile):
            pass

        guid = TestGuidFile()
        guid._metadata_cache = {'name': 'test'}

        assert_equals(getattr(guid, 'name', 'foo'), 'test')


def assert_urls_equal(url1, url2):
    furl1 = furl.furl(url1)
    furl2 = furl.furl(url2)
    for attr in ['scheme', 'host', 'port']:
        setattr(furl1, attr, None)
        setattr(furl2, attr, None)
    assert_equal(furl1, furl2)


class TestAddonFileViews(OsfTestCase):

    def setUp(self):
        super(TestAddonFileViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.user.add_addon('github')
        self.project.add_addon('github', auth=Auth(self.user))

        self.user_addon = self.user.get_addon('github')
        self.node_addon = self.project.get_addon('github')
        self.oauth = AddonGitHubOauthSettings(
            github_user_id='denbarell',
            oauth_access_token='Truthy'
        )

        self.oauth.save()

        self.user_addon.oauth_settings = self.oauth
        self.user_addon.save()

        self.node_addon.user_settings = self.user_addon
        self.node_addon.save()

        # self.node_addon.user_settings = 'Truthy'
        # setattr(self.node_addon, 'has_auth', True)

    def get_mako_return(self):
        ret = serialize_node(self.project, Auth(self.user), primary=True)
        ret.update({
            'extra': '',
            'provider': '',
            'rendered': '',
            'file_path': '',
            'files_url': '',
            'file_name': '',
            'render_url': '',
            'materialized_path': '',
        })
        ret.update(rubeus.collect_addon_assets(self.project))
        return ret

    def test_redirects_to_guid(self):
        path = 'bigdata'
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=path,
                provider='github'
            ),
            auth=self.user.auth
        )

        assert_equals(resp.status_code, 302)
        assert_equals(resp.headers['Location'], 'http://localhost:80{}'.format(guid.guid_url))

    def test_action_download_redirects_to_download(self):
        path = 'cloudfiles'
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        resp = self.app.get(guid.guid_url + '?action=download', auth=self.user.auth)

        assert_equals(resp.status_code, 302)
        assert_equals(resp.headers['Location'], guid.download_url + '&action=download')

    @mock.patch('website.addons.base.request')
    def test_public_download_url_includes_view_only(self, mock_request):
        view_only = 'justworkplease'
        mock_request.args = {
            'view_only': view_only
        }

        path = 'cloudfiles'
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        assert_in('view_only={}'.format(view_only), guid.public_download_url)

    @mock.patch('website.addons.base.views.addon_view_file')
    def test_action_view_calls_view_file(self, mock_view_file):
        self.user.reload()
        self.project.reload()

        path = 'cloudfiles'
        mock_view_file.return_value = self.get_mako_return()
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        self.app.get(guid.guid_url + '?action=view', auth=self.user.auth)

        args, kwargs = mock_view_file.call_args
        assert_equals(kwargs, {})
        assert_equals(args[-1], {'action': 'view'})
        assert_equals(args[1], self.project)
        assert_equals(args[0].user, self.user)
        assert_equals(args[2], self.node_addon)

    @mock.patch('website.addons.base.views.addon_view_file')
    def test_no_action_calls_view_file(self, mock_view_file):
        self.user.reload()
        self.project.reload()

        path = 'cloudfiles'
        mock_view_file.return_value = self.get_mako_return()
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        self.app.get(guid.guid_url, auth=self.user.auth)

        args, kwargs = mock_view_file.call_args
        assert_equals(kwargs, {})
        assert_equals(args[-1], {})
        assert_equals(args[1], self.project)
        assert_equals(args[0].user, self.user)
        assert_equals(args[2], self.node_addon)

    def test_download_create_guid(self):
        path = 'cloudfiles'

        self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=path,
                provider='github',
                action='download'
            ),
            auth=self.user.auth
        )

        guid, created = self.node_addon.find_or_create_file_guid('/' + path)

        assert_true(guid)
        assert_false(created)
        assert_equals(guid.waterbutler_path, '/' + path)

    def test_unauthorized_addons_raise(self):
        path = 'cloudfiles'
        self.node_addon.user_settings = None
        self.node_addon.save()

        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=path,
                provider='github',
                action='download'
            ),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equals(resp.status_code, 403)

    def test_head_returns_url(self):
        path = 'the little engine that couldnt'
        guid, _ = self.node_addon.find_or_create_file_guid('/' + path)

        download_url = furl.furl(guid.download_url)
        download_url.args['accept_url'] = 'false'

        resp = self.app.head(guid.guid_url, auth=self.user.auth)

        assert_urls_equal(resp.headers['Location'], download_url.url)

    def test_nonexistent_addons_raise(self):
        path = 'cloudfiles'
        self.project.delete_addon('github', Auth(self.user))
        self.project.save()

        resp = self.app.get(
            self.project.api_url_for(
                'addon_render_file',
                path=path,
                provider='github',
                action='download'
            ),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equals(resp.status_code, 400)

    def test_unauth_addons_raise(self):
        path = 'cloudfiles'
        self.node_addon.user_settings = None
        self.node_addon.save()

        resp = self.app.get(
            self.project.api_url_for(
                'addon_render_file',
                path=path,
                provider='github',
                action='download'
            ),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equals(resp.status_code, 401)

    def test_unconfigured_addons_raise(self):
        path = 'cloudfiles'
        self.node_addon.repo = None
        self.node_addon.save()

        resp = self.app.get(
            self.project.api_url_for(
                'addon_render_file',
                path=path,
                provider='github',
                action='download'
            ),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equals(resp.status_code, 400)


class TestLegacyViews(OsfTestCase):

    def setUp(self):
        super(TestLegacyViews, self).setUp()
        self.path = 'mercury.png'
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = self.project.get_addon('osfstorage')
        file_record = self.node_addon.root_node.append_file(self.path)
        self.expected_path = file_record._id
        self.node_addon.save()
        file_record.save()

    def test_view_file_redirect(self):
        url = '/{0}/osffiles/{1}/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.expected_path,
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_redirect(self):
        url = '/{0}/osffiles/{1}/download/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_version_redirect(self):
        url = '/{0}/osffiles/{1}/version/3/download/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            version=3,
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_redirect(self):
        url = '/api/v1/project/{0}/osffiles/{1}/'.format(self.project._id, self.path)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_version_redirect(self):
        url = '/api/v1/project/{0}/osffiles/{1}/version/3/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            version=3,
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_no_provider_name(self):
        url = '/{0}/files/{1}'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.expected_path,
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_action_as_param(self):
        url = '/{}/osfstorage/files/{}/?action=download'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_other_addon_redirect(self):
        url = '/project/{0}/mycooladdon/files/{1}/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.path,
            provider='mycooladdon',
        )
        assert_urls_equal(res.location, expected_url)

    def test_other_addon_redirect_download(self):
        url = '/project/{0}/mycooladdon/files/{1}/download/'.format(
            self.project._id,
            self.path,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 301)
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.path,
            action='download',
            provider='mycooladdon',
        )
        assert_urls_equal(res.location, expected_url)
