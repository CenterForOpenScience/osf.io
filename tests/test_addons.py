# -*- coding: utf-8 -*-

import time
import mock
import datetime
import unittest
from nose.tools import *  # noqa
import httplib as http

import jwe
import jwt
import furl
import itsdangerous
from modularodm import storage, Q

from framework.auth import cas
from framework.auth import signing
from framework.auth.core import Auth
from framework.exceptions import HTTPError
from framework.sessions.model import Session
from framework.mongo import set_up_storage
from tests import factories

from website import settings
from website.files import models
from website.files.models.base import PROVIDER_MAP, StoredFileNode, TrashedFileNode
from website.project.model import MetaSchema, ensure_schemas
from website.util import api_url_for, rubeus
from website.project import new_private_link
from website.project.views.node import _view_project as serialize_node
from website.addons.base import AddonConfig, AddonNodeSettingsBase, views
from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory
from website.addons.github.exceptions import ApiError
from website.addons.github.tests.factories import GitHubAccountFactory


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
        self.user = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user)
        self.session = Session(data={'auth_user_id': self.user._id})
        self.session.save()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session._id)
        self.configure_addon()
        self.JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))

    def configure_addon(self):
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')
        self.oauth_settings = GitHubAccountFactory(display_name='john')
        self.oauth_settings.save()
        self.user.external_accounts.append(self.oauth_settings)
        self.user.save()
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth_settings
        self.node_addon.save()

    def build_url(self, **kwargs):
        options = {'payload': jwe.encrypt(jwt.encode({'data': dict(dict(
            action='download',
            nid=self.node._id,
            provider=self.node_addon.config.short_name,
            ), **kwargs),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        }, settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM), self.JWE_KEY)}
        return api_url_for('get_auth', **options)

    def test_auth_download(self):
        url = self.build_url()
        res = self.app.get(url, auth=self.user.auth)
        data = jwt.decode(jwe.decrypt(res.json['payload'].encode('utf-8'), self.JWE_KEY), settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM)['data']
        assert_equal(data['auth'], views.make_auth(self.user))
        assert_equal(data['credentials'], self.node_addon.serialize_waterbutler_credentials())
        assert_equal(data['settings'], self.node_addon.serialize_waterbutler_settings())
        expected_url = furl.furl(self.node.api_url_for('create_waterbutler_log', _absolute=True))
        observed_url = furl.furl(data['callback_url'])
        observed_url.port = expected_url.port
        assert_equal(expected_url, observed_url)

    def test_auth_missing_args(self):
        url = self.build_url(cookie=None)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_auth_bad_cookie(self):
        url = self.build_url(cookie=self.cookie)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 200)
        data = jwt.decode(jwe.decrypt(res.json['payload'].encode('utf-8'), self.JWE_KEY), settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM)['data']
        assert_equal(data['auth'], views.make_auth(self.user))
        assert_equal(data['credentials'], self.node_addon.serialize_waterbutler_credentials())
        assert_equal(data['settings'], self.node_addon.serialize_waterbutler_settings())
        expected_url = furl.furl(self.node.api_url_for('create_waterbutler_log', _absolute=True))
        observed_url = furl.furl(data['callback_url'])
        observed_url.port = expected_url.port
        assert_equal(expected_url, observed_url)

    def test_auth_cookie(self):
        url = self.build_url(cookie=self.cookie[::-1])
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_auth_missing_addon(self):
        url = self.build_url(provider='queenhub')
        res = self.app.get(url, expect_errors=True, auth=self.user.auth)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.base.views.cas.get_client')
    def test_auth_bad_bearer_token(self, mock_cas_client):
        mock_cas_client.return_value = mock.Mock(profile=mock.Mock(return_value=cas.CasResponse(authenticated=False)))
        url = self.build_url()
        res = self.app.get(url, headers={'Authorization': 'Bearer invalid_access_token'}, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestAddonLogs(OsfTestCase):

    def setUp(self):
        super(TestAddonLogs, self).setUp()
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
        self.oauth_settings = GitHubAccountFactory(display_name='john')
        self.oauth_settings.save()
        self.user.external_accounts.append(self.oauth_settings)
        self.user.save()        
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth_settings
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

    @mock.patch('website.notifications.events.files.FileAdded.perform')
    def test_add_log(self, mock_perform):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path})
        nlogs = len(self.node.logs)
        self.app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs + 1)
        # # Mocking form_message and perform so that the payload need not be exact.
        # assert_true(mock_form_message.called, "form_message not called")
        assert_true(mock_perform.called, "perform not called")

    def test_add_log_missing_args(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, auth=None)
        nlogs = len(self.node.logs)
        res = self.app.put_json(
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
        res = self.app.put_json(
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
        res = self.app.put_json(
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
        res = self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.node.reload()
        assert_equal(len(self.node.logs), nlogs)

    def test_action_file_rename(self):
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(
            action='rename',
            metadata={
                'path': 'foo',
            },
            source={
                'materialized': 'foo',
                'provider': 'github',
                'node': {'_id': self.node._id},
                'name': 'new.txt',
                'kind': 'file',
            },
            destination={
                'path': 'foo',
                'materialized': 'foo',
                'provider': 'github',
                'node': {'_id': self.node._id},
                'name': 'old.txt',
                'kind': 'file',
            },
        )
        self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'}
        )
        self.node.reload()

        assert_equal(
            self.node.logs[-1].action,
            'github_addon_file_renamed',
        )


class TestCheckAuth(OsfTestCase):

    def setUp(self):
        super(TestCheckAuth, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_has_permission(self):
        res = views.check_access(self.node, Auth(user=self.user), 'upload', None)
        assert_true(res)

    def test_not_has_permission_read_public(self):
        self.node.is_public = True
        self.node.save()
        res = views.check_access(self.node, Auth(), 'download', None)

    def test_not_has_permission_read_has_link(self):
        link = new_private_link('red-special', self.user, [self.node], anonymous=False)
        res = views.check_access(self.node, Auth(private_key=link.key), 'download', None)

    def test_not_has_permission_logged_in(self):
        user2 = AuthUserFactory()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.node, Auth(user=user2), 'download', None)
        assert_equal(exc_info.exception.code, 403)

    def test_not_has_permission_not_logged_in(self):
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.node, Auth(), 'download', None)
        assert_equal(exc_info.exception.code, 401)

    def test_has_permission_on_parent_node_copyto_pass_if_registration(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, parent=self.node)
        component.is_registration = True

        assert_false(component.has_permission(self.user, 'write'))
        res = views.check_access(component, Auth(user=self.user), 'copyto', None)
        assert_true(res)

    def test_has_permission_on_parent_node_copyto_fail_if_not_registration(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, parent=self.node)

        assert_false(component.has_permission(self.user, 'write'))
        with assert_raises(HTTPError):
            views.check_access(component, Auth(user=self.user), 'copyto', None)

    def test_has_permission_on_parent_node_copyfrom(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)

        assert_false(component.has_permission(self.user, 'write'))
        res = views.check_access(component, Auth(user=self.user), 'copyfrom', None)
        assert_true(res)

class TestCheckPreregAuth(OsfTestCase):

    def setUp(self):
        super(TestCheckPreregAuth, self).setUp()

        ensure_schemas()
        self.prereg_challenge_admin_user = AuthUserFactory()
        self.prereg_challenge_admin_user.system_tags.append(settings.PREREG_ADMIN_TAG)
        self.prereg_challenge_admin_user.save()
        prereg_schema = MetaSchema.find_one(
                Q('name', 'eq', 'Prereg Challenge') &
                Q('schema_version', 'eq', 2)
        )

        self.user = AuthUserFactory()
        self.node = factories.ProjectFactory(creator=self.user)

        self.parent = factories.ProjectFactory()
        self.child = factories.NodeFactory(parent=self.parent)

        self.draft_registration = factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema,
            branched_from=self.parent
        )

    def test_has_permission_download_prereg_challenge_admin(self):
        res = views.check_access(self.draft_registration.branched_from,
            Auth(user=self.prereg_challenge_admin_user), 'download', None)
        assert_true(res)

    def test_has_permission_download_on_component_prereg_challenge_admin(self):
        try:
            res = views.check_access(self.draft_registration.branched_from.nodes[0],
                                     Auth(user=self.prereg_challenge_admin_user), 'download', None)
        except Exception:
            self.fail()
        assert_true(res)

    def test_has_permission_download_not_prereg_challenge_admin(self):
        new_user = AuthUserFactory()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.draft_registration.branched_from,
                 Auth(user=new_user), 'download', None)
            assert_equal(exc_info.exception.code, http.FORBIDDEN)

    def test_has_permission_download_prereg_challenge_admin_not_draft(self):
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.node,
                 Auth(user=self.prereg_challenge_admin_user), 'download', None)
            assert_equal(exc_info.exception.code, http.FORBIDDEN)

    def test_has_permission_write_prereg_challenge_admin(self):
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.draft_registration.branched_from,
                Auth(user=self.prereg_challenge_admin_user), 'write', None)
            assert_equal(exc_info.exception.code, http.FORBIDDEN)

class TestCheckOAuth(OsfTestCase):

    def setUp(self):
        super(TestCheckOAuth, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_has_permission_private_not_authenticated(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=False)

        assert_false(component.has_permission(self.user, 'write'))
        with assert_raises(HTTPError) as exc_info:
            views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_equal(exc_info.exception.code, 403)

    def test_has_permission_private_no_scope_forbidden(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {}})

        assert_false(component.has_permission(self.user, 'write'))
        with assert_raises(HTTPError) as exc_info:
            views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_equal(exc_info.exception.code, 403)

    def test_has_permission_public_irrelevant_scope_allowed(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=True, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.users.all_read'}})

        assert_false(component.has_permission(self.user, 'write'))
        res = views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_true(res)

    def test_has_permission_private_irrelevant_scope_forbidden(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.users.all_read'}})

        assert_false(component.has_permission(self.user, 'write'))
        with assert_raises(HTTPError) as exc_info:
            views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_equal(exc_info.exception.code, 403)

    def test_has_permission_decommissioned_scope_no_error(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {
                                       'decommissioned.scope+write',
                                       'osf.nodes.data_read',
                                   }})

        assert_false(component.has_permission(self.user, 'write'))
        res = views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_true(res)

    def test_has_permission_write_scope_read_action(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.nodes.data_write'}})

        assert_false(component.has_permission(self.user, 'write'))
        res = views.check_access(component, Auth(user=self.user), 'download', cas_resp)
        assert_true(res)

    def test_has_permission_read_scope_write_action_forbidden(self):
        component = ProjectFactory(creator=self.user, is_public=False, parent=self.node)
        cas_resp = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.nodes.data_read'}})

        assert_true(component.has_permission(self.user, 'write'))
        with assert_raises(HTTPError) as exc_info:
            views.check_access(component, Auth(user=self.user), 'upload', cas_resp)
        assert_equal(exc_info.exception.code, 403)


def assert_urls_equal(url1, url2):
    furl1 = furl.furl(url1)
    furl2 = furl.furl(url2)
    for attr in ['scheme', 'host', 'port']:
        setattr(furl1, attr, None)
        setattr(furl2, attr, None)
    # Note: furl params are ordered and cause trouble
    assert_equal(dict(furl1.args), dict(furl2.args))
    furl1.args = {}
    furl2.args = {}
    assert_equal(furl1, furl2)


class TestFileNode(models.FileNode):
    provider = 'test_addons'

    def touch(self, bearer, version=None, revision=None, **kwargs):
        if version:
            if self.versions:
                try:
                    return self.versions[int(version) - 1]
                except (IndexError, ValueError):
                    return None
            else:
                return None
        return models.FileVersion()


class TestFile(TestFileNode, models.File):
    pass


class TestFolder(TestFileNode, models.Folder):
    pass


@mock.patch('website.addons.github.model.GitHubClient.repo', mock.Mock(side_effect=ApiError))
class TestAddonFileViews(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestAddonFileViews, cls).setUpClass()
        PROVIDER_MAP['github'] = [TestFolder, TestFile, TestFileNode]
        TestFileNode.provider = 'github'

    def setUp(self):
        super(TestAddonFileViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.user.add_addon('github')
        self.project.add_addon('github', auth=Auth(self.user))

        self.user_addon = self.user.get_addon('github')
        self.node_addon = self.project.get_addon('github')
        self.oauth = GitHubAccountFactory()
        self.oauth.save()

        self.user.external_accounts.append(self.oauth)
        self.user.save()

        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth
        self.node_addon.repo = 'Truth'
        self.node_addon.user = 'E'
        self.node_addon.save()

    @classmethod
    def tearDownClass(cls):
        super(TestAddonFileViews, cls).tearDownClass()
        PROVIDER_MAP['github'] = [models.GithubFolder, models.GithubFile, models.GithubFileNode]
        del PROVIDER_MAP['test_addons']
        TrashedFileNode.remove()

    def get_test_file(self):
        version = models.FileVersion(identifier='1')
        version.save()
        versions = [version]
        ret = TestFile(
            name='Test',
            node=self.project,
            path='/test/Test',
            materialized_path='/test/Test',
            versions=versions
        )
        ret.save()
        return ret

    def get_mako_return(self):
        ret = serialize_node(self.project, Auth(self.user), primary=True)
        ret.update({
            'error': '',
            'provider': '',
            'file_path': '',
            'sharejs_uuid': '',
            'private': '',
            'urls': {
                'files': '',
                'render': '',
                'sharejs': '',
                'mfr': '',
                'gravatar': '',
                'external': '',
            },
            'size': '',
            'extra': '',
            'file_name': '',
            'materialized_path': '',
            'file_id': '',
        })
        ret.update(rubeus.collect_addon_assets(self.project))
        return ret

    def test_redirects_to_guid(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=file_node.path.strip('/'),
                provider='github'
            ),
            auth=self.user.auth
        )

        assert_equals(resp.status_code, 302)
        assert_equals(resp.location, 'http://localhost:80/{}/'.format(guid._id))

    def test_action_download_redirects_to_download(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get('/{}/?action=download'.format(guid._id), auth=self.user.auth)

        assert_equals(resp.status_code, 302)
        location = furl.furl(resp.location)
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(action='download', direct=None, version=None))

    def test_action_download_redirects_to_download_with_version(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get('/{}/?action=download&revision=1'.format(guid._id), auth=self.user.auth)

        assert_equals(resp.status_code, 302)
        location = furl.furl(resp.location)
        # Note: version is added but us but all other url params are added as well
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(action='download', direct=None, revision=1, version=None))

    @mock.patch('website.addons.base.views.addon_view_file')
    def test_action_view_calls_view_file(self, mock_view_file):
        self.user.reload()
        self.project.reload()

        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        mock_view_file.return_value = self.get_mako_return()

        self.app.get('/{}/?action=view'.format(guid._id), auth=self.user.auth)

        args, kwargs = mock_view_file.call_args
        assert_equals(kwargs, {})
        assert_equals(args[0].user._id, self.user._id)
        assert_equals(args[1], self.project)
        assert_equals(args[2], file_node)
        assert_true(isinstance(args[3], file_node.touch(None).__class__))

    @mock.patch('website.addons.base.views.addon_view_file')
    def test_no_action_calls_view_file(self, mock_view_file):
        self.user.reload()
        self.project.reload()

        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        mock_view_file.return_value = self.get_mako_return()

        self.app.get('/{}/'.format(guid._id), auth=self.user.auth)

        args, kwargs = mock_view_file.call_args
        assert_equals(kwargs, {})
        assert_equals(args[0].user._id, self.user._id)
        assert_equals(args[1], self.project)
        assert_equals(args[2], file_node)
        assert_true(isinstance(args[3], file_node.touch(None).__class__))

    def test_download_create_guid(self):
        file_node = self.get_test_file()
        assert_is(file_node.get_guid(), None)

        self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=file_node.path.strip('/'),
                provider='github',
            ),
            auth=self.user.auth
        )

        assert_true(file_node.get_guid())

    def test_view_file_does_not_delete_file_when_requesting_invalid_version(self):
        with mock.patch('website.addons.github.model.GitHubNodeSettings.is_private',
                        new_callable=mock.PropertyMock) as mock_is_private:
            mock_is_private.return_value = False

            file_node = self.get_test_file()
            assert_is(file_node.get_guid(), None)

            url = self.project.web_url_for(
                'addon_view_or_download_file',
                path=file_node.path.strip('/'),
                provider='github',
            )
            # First view generated GUID
            self.app.get(url, auth=self.user.auth)

            self.app.get(url + '?version=invalid', auth=self.user.auth, expect_errors=True)

            assert_is_not_none(StoredFileNode.load(file_node._id))
            assert_is_none(TrashedFileNode.load(file_node._id))

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

        assert_equals(resp.status_code, 401)

    def test_nonstorage_addons_raise(self):
        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path='sillywiki',
                provider='wiki',
                action='download'
            ),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equals(resp.status_code, 400)

    def test_head_returns_url(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.head('/{}/'.format(guid._id), auth=self.user.auth)
        location = furl.furl(resp.location)
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(direct=None, version=None))

    def test_head_returns_url_with_version(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.head('/{}/?revision=1&foo=bar'.format(guid._id), auth=self.user.auth)
        location = furl.furl(resp.location)
        # Note: version is added but us but all other url params are added as well
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(direct=None, revision=1, version=None, foo='bar'))

    def test_nonexistent_addons_raise(self):
        path = 'cloudfiles'
        self.project.delete_addon('github', Auth(self.user))
        self.project.save()

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

        assert_equals(resp.status_code, 400)

    def test_unauth_addons_raise(self):
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

        assert_equals(resp.status_code, 401)

    def test_delete_action_creates_trashed_file_node(self):
        file_node = self.get_test_file()
        payload = {
            'provider': file_node.provider,
            'metadata': {
                'path': '/test/Test',
                'materialized': '/test/Test'
            }
        }
        views.addon_delete_file_node(self=None, node=self.project, user=self.user, event_type='file_removed', payload=payload)
        assert_false(StoredFileNode.load(file_node._id))
        assert_true(TrashedFileNode.load(file_node._id))

    def test_delete_action_for_folder_deletes_subfolders_and_creates_trashed_file_nodes(self):
        file_node = self.get_test_file()
        subfolder = TestFolder(
            name='folder',
            node=self.project,
            path='/test/folder/',
            materialized_path='/test/folder/',
            versions=[]
        )
        subfolder.save()
        payload = {
            'provider': file_node.provider,
            'metadata': {
                'path': '/test/',
                'materialized': '/test/'
            }
        }
        views.addon_delete_file_node(self=None, node=self.project, user=self.user, event_type='file_removed', payload=payload)
        assert_false(StoredFileNode.load(file_node._id))
        assert_true(TrashedFileNode.load(file_node._id))
        assert_false(StoredFileNode.load(subfolder._id))


class TestLegacyViews(OsfTestCase):

    def setUp(self):
        super(TestLegacyViews, self).setUp()
        self.path = 'mercury.png'
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = self.project.get_addon('osfstorage')
        file_record = self.node_addon.get_root().append_file(self.path)
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
