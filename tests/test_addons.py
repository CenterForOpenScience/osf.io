import datetime
import time
import functools
import logging
from importlib import import_module
from unittest.mock import Mock

from furl import furl
import itsdangerous
import jwe
import jwt
from unittest import mock
import pytest
from django.utils import timezone
from framework.auth import cas, signing
from framework.auth.core import Auth
from framework.exceptions import HTTPError
from tests.base import OsfTestCase, get_default_metaschema
from api_tests.utils import create_test_file
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    DraftRegistrationFactory,
)
from website import settings
from addons.base import views
from addons.github.exceptions import ApiError
from addons.github.models import GithubFolder, GithubFile, GithubFileNode
from addons.github.tests.factories import GitHubAccountFactory
from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder, OsfStorageFile
from addons.osfstorage.tests.factories import FileVersionFactory
from osf import features
from osf.models import files as file_models
from osf.models.files import BaseFileNode, TrashedFileNode
from osf.utils.permissions import WRITE, READ
from website.project import new_private_link
from website.project.views.node import _view_project as serialize_node
from website.project.views.node import serialize_addons, collect_node_config_js
from website.util import api_url_for, rubeus
from api.caching import settings as cache_settings
from addons.osfstorage import settings as osfstorage_settings
from api.caching.utils import storage_usage_cache
from dateutil.parser import parse as parse_date
from framework import sentry
from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from website.settings import EXTERNAL_EMBER_APPS
from waffle.testutils import override_flag
from django.conf import settings as django_conf_settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


class TestAddonAuth(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user)
        self.session = SessionStore()
        self.session['auth_user_id'] = self.user._id
        self.session.create()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session.session_key).decode()
        self.configure_addon()
        self.JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))

    def configure_addon(self):
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')
        self.oauth_settings = GitHubAccountFactory(display_name='john')
        self.oauth_settings.save()
        self.user.external_accounts.add(self.oauth_settings)
        self.user.save()
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth_settings
        self.node_addon.save()
        self.user_addon.oauth_grants[self.node._id] = {self.oauth_settings._id: []}
        self.user_addon.save()

    def build_url(self, **kwargs):
        options = {'payload': jwe.encrypt(jwt.encode({'data': dict(dict(
            action='download',
            nid=self.node._id,
            metrics={'uri': settings.MFR_SERVER_URL},
            provider=self.node_addon.config.short_name), **kwargs),
            'exp': timezone.now() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        }, settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM).encode(), self.JWE_KEY)}
        return api_url_for('get_auth', **options)

    def test_auth_download(self):
        url = self.build_url()
        res = self.app.get(url, auth=self.user.auth)
        data = jwt.decode(jwe.decrypt(res.json['payload'].encode('utf-8'), self.JWE_KEY), settings.WATERBUTLER_JWT_SECRET, algorithms=[settings.WATERBUTLER_JWT_ALGORITHM])['data']
        assert data['auth'] == views.make_auth(self.user)
        assert data['credentials'] == self.node_addon.serialize_waterbutler_credentials()
        assert data['settings'] == self.node_addon.serialize_waterbutler_settings()
        expected_url = furl(self.node.api_url_for('create_waterbutler_log', _absolute=True, _internal=True))
        observed_url = furl(data['callback_url'])
        observed_url.port = expected_url.port
        assert expected_url == observed_url

    def test_auth_render_action_returns_200(self):
        url = self.build_url(action='render')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
    def test_auth_render_action_requires_read_permission(self):
        node = ProjectFactory(is_public=False)
        url = self.build_url(action='render', nid=node._id)
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 403

    def test_auth_export_action_returns_200(self):
        url = self.build_url(action='export')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200

    def test_auth_export_action_requires_read_permission(self):
        node = ProjectFactory(is_public=False)
        url = self.build_url(action='export', nid=node._id)
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 403

    def test_auth_missing_args(self):
        url = self.build_url(cookie=None)
        res = self.app.get(url)
        assert res.status_code == 401

    def test_auth_bad_cookie(self):
        url = self.build_url(cookie=self.cookie)
        res = self.app.get(url)
        assert res.status_code == 200
        data = jwt.decode(
            jwe.decrypt(res.json['payload'].encode('utf-8'), self.JWE_KEY),
            settings.WATERBUTLER_JWT_SECRET,
            algorithms=[settings.WATERBUTLER_JWT_ALGORITHM]
        )['data']
        assert data['auth'] == views.make_auth(self.user)
        assert data['credentials'] == self.node_addon.serialize_waterbutler_credentials()
        assert data['settings'] == self.node_addon.serialize_waterbutler_settings()
        expected_url = furl(self.node.api_url_for('create_waterbutler_log', _absolute=True, _internal=True))
        observed_url = furl(data['callback_url'])
        observed_url.port = expected_url.port
        assert expected_url == observed_url

    def test_auth_cookie(self):
        url = self.build_url(cookie=self.cookie[::-1])
        res = self.app.get(url)
        assert res.status_code == 401

    def test_auth_missing_addon(self):
        url = self.build_url(provider='queenhub')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 400

    @mock.patch('addons.base.views.cas.get_client')
    def test_auth_bad_bearer_token(self, mock_cas_client):
        mock_cas_client.return_value = mock.Mock(profile=mock.Mock(return_value=cas.CasResponse(authenticated=False)))
        url = self.build_url()
        res = self.app.get(url, headers={'Authorization': 'Bearer invalid_access_token'}, )
        assert res.status_code == 403

    def test_action_render_marks_version_as_seen(self):
        noncontrib = AuthUserFactory()
        node = ProjectFactory(is_public=True)
        test_file = create_test_file(node, self.user)
        url = self.build_url(nid=node._id, action='render', provider='osfstorage', path=test_file.path)
        res = self.app.get(url, auth=noncontrib.auth)
        assert res.status_code == 200

        # Add a new version, make sure that does not have a record
        version = FileVersionFactory()
        test_file.add_version(version)
        test_file.save()

        versions = test_file.versions.order_by('created')
        assert versions.first().seen_by.filter(guids___id=noncontrib._id).exists()
        assert not versions.last().seen_by.filter(guids___id=noncontrib._id).exists()

    def test_action_download_contrib(self):
        test_file = create_test_file(self.node, self.user)
        url = self.build_url(action='download', provider='osfstorage', path=test_file.path, version=1)
        nlogs = self.node.logs.count()
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200

        test_file.reload()
        assert test_file.get_download_count() == 0 # contribs don't count as downloads
        assert self.node.logs.count() == nlogs # don't log downloads

    def test_action_download_non_contrib(self):
        noncontrib = AuthUserFactory()
        node = ProjectFactory(is_public=True)
        test_file = create_test_file(node, self.user)
        url = self.build_url(nid=node._id, action='download', provider='osfstorage', path=test_file.path, version=1)
        nlogs = node.logs.count()
        res = self.app.get(url, auth=noncontrib.auth)
        assert res.status_code == 200

        test_file.reload()
        assert test_file.get_download_count() == 1
        assert node.logs.count() == nlogs # don't log views

    def test_action_download_mfr_views_contrib(self):
        test_file = create_test_file(self.node, self.user)
        url = self.build_url(action='render', provider='osfstorage', path=test_file.path, version=1)
        nlogs = self.node.logs.count()
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200

        test_file.reload()
        assert test_file.get_view_count() == 0 # contribs don't count as views
        assert self.node.logs.count() == nlogs # don't log views

    def test_action_download_mfr_views_non_contrib(self):
        noncontrib = AuthUserFactory()
        node = ProjectFactory(is_public=True)
        test_file = create_test_file(node, self.user)
        url = self.build_url(nid=node._id, action='render', provider='osfstorage', path=test_file.path, version=1)
        nlogs = node.logs.count()
        res = self.app.get(url, auth=noncontrib.auth)
        assert res.status_code == 200

        test_file.reload()
        assert test_file.get_view_count() == 1
        assert node.logs.count() == nlogs # don't log views


class TestAddonLogs(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user_non_contrib = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user)
        self.node2 = ProjectFactory(creator=self.user)
        self.file = OsfStorageFileNode.create(
            target=self.node,
            path='/testfile',
            _id='testfile',
            name='testfile',
            materialized_path='/testfile'
        )
        self.file2 = OsfStorageFile.create(
            target=self.node,
            path='/lollipop',
            _id='lollipop',
            name='lollipop',
            materialized_path='/lollipop'
        )
        self.file.save()
        self.file2.save()
        self.session = SessionStore()
        self.session['auth_user_id'] = self.user._id
        self.session.create()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session.session_key)
        self.configure_addon()

    def configure_addon(self):
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')
        self.oauth_settings = GitHubAccountFactory(display_name='john')
        self.oauth_settings.save()
        self.user.external_accounts.add(self.oauth_settings)
        self.user.save()
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth_settings
        self.node_addon.save()
        self.user_addon.oauth_grants[self.node._id] = {self.oauth_settings._id: []}
        self.user_addon.save()

    def configure_osf_addon(self):
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = self.project.get_addon('osfstorage')
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
            for key, value in options.items()
            if value is not None
        }
        message, signature = signing.default_signer.sign_payload(options)
        return {
            'payload': message,
            'signature': signature,
        }

    def build_payload_with_dest(self, destination, **kwargs):
        options = dict(
            auth={'id': self.user._id},
            action='create',
            provider=self.node_addon.config.short_name,
            destination=destination,
            time=time.time() + 1000,
        )
        options.update(kwargs)
        options = {
            key: value
            for key, value in options.items()
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
        payload = self.build_payload(metadata={'nid': self.node._id, 'path': path})
        nlogs = self.node.logs.count()
        self.app.put(url, json=payload)
        self.node.reload()
        assert self.node.logs.count() == nlogs + 1
        # # Mocking form_message and perform so that the payload need not be exact.
        # assert mock_form_message.called, "form_message not called"
        assert mock_perform.called, 'perform not called'

    def test_add_log_missing_args(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, auth=None)
        nlogs = self.node.logs.count()
        res = self.app.put(
            url,
            json=payload,
        )
        assert res.status_code == 400
        self.node.reload()
        assert self.node.logs.count() == nlogs

    def test_add_log_no_user(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, auth={'id': None})
        nlogs = self.node.logs.count()
        res = self.app.put(
            url,
            json=payload,
        )
        assert res.status_code == 400
        self.node.reload()
        assert self.node.logs.count() == nlogs

    def test_add_log_no_addon(self):
        path = 'pizza'
        node = ProjectFactory(creator=self.user)
        url = node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path})
        nlogs = node.logs.count()
        res = self.app.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
        )
        assert res.status_code == 400
        self.node.reload()
        assert node.logs.count() == nlogs

    def test_add_log_bad_action(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'path': path}, action='dance')
        nlogs = self.node.logs.count()
        res = self.app.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
        )
        assert res.status_code == 400
        self.node.reload()
        assert self.node.logs.count() == nlogs

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
        self.app.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        self.node.reload()

        assert self.node.logs.latest().action == 'github_addon_file_renamed'

    def test_action_file_rename_storage(self):
        url = self.node.api_url_for('create_waterbutler_log')
        current_usage = self.node.storage_usage
        payload = self.build_payload(
            action='rename',
            metadata={
                'path': 'foo',
            },
            source={
                'materialized': 'foo',
                'provider': 'osfstorage',
                'node': {'_id': self.node._id},
                'name': 'new.txt',
                'kind': 'file',
            },
            destination={
                'path': 'foo',
                'materialized': 'foo',
                'provider': 'osf_storage',
                'node': {'_id': self.node._id},
                'name': 'old.txt',
                'kind': 'file',
            },
        )
        self.app.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        self.node.reload()

        assert self.node.storage_usage == current_usage

    def test_add_log_updates_cache_rename_via_move(self):
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 250

        payload = self.build_payload_with_dest(
            action='move',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'old.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 250

    def test_action_downloads_contrib(self):
        url = self.node.api_url_for('create_waterbutler_log')
        download_actions=('download_file', 'download_zip')
        base_url = self.node.osfstorage_region.waterbutler_url
        wb_url = base_url + '?version=1'
        for action in download_actions:
            payload = self.build_payload(metadata={'path': '/testfile',
                                                   'nid': self.node._id},
                                         action_meta={'is_mfr_render': False},
                                         request_meta={'url': wb_url},
                                         action=action)
            nlogs = self.node.logs.count()
            res = self.app.put(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
            )
            assert res.status_code == 200

        self.node.reload()
        assert self.node.logs.count() == nlogs

    def test_add_file_osfstorage_log(self):
        self.configure_osf_addon()
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path})
        nlogs = self.node.logs.count()
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert self.node.logs.count() == nlogs + 1
        assert ('urls' in self.node.logs.filter(action='osf_storage_file_added')[0].params)

    def test_add_log_updates_cache_create(self):
        self.configure_osf_addon()
        path = 'lollipop'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={
            'materialized': path,
            'kind': 'file',
            'path': path,
            'sizeInt': 100,
            'size': 100,
            'nid': self.node._id,
        })
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert self.node.storage_usage == 100

    def test_add_log_updates_cache_update(self):
        self.configure_osf_addon()
        path = 'lollipop'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={
            'materialized': path,
            'kind': 'file',
            'path': path,
            'sizeInt': 120,
            'size': 120,
            'nid': self.node._id,
        }, action='update')
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert self.node.storage_usage == 120

        payload = self.build_payload(metadata={
            'materialized': path,
            'kind': 'file',
            'path': path,
            'sizeInt': 140,
            'size': 140,
            'nid': self.node._id,
        }, action='update')

        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})
        self.node.reload()
        assert self.node.storage_usage == 260

    def test_add_log_updates_cache_move(self):
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 250

        payload = self.build_payload_with_dest(
            action='move',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node2._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 0

        self.node2.reload()
        assert self.node2.storage_usage == 250

    def test_add_log_updates_cache_move_multiversion(self):
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        self.file2.create_version(self.user, {
            'object': '06d80f',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 275,
            'size': 275,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 525

        payload = self.build_payload_with_dest(
            action='move',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node2._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 0

        self.node2.reload()
        assert self.node2.storage_usage == 525

    def test_add_log_updates_cache_move_outside_osf(self):
        ''' Moving a file object out of osfstorage '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 250

        payload = self.build_payload_with_dest(
            action='move',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'github',
                'nid': self.node._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 0

    def test_add_log_updates_cache_move_into_osf(self):
        ''' Moving file from outside osf into osf storage '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')

        payload = self.build_payload_with_dest(
            action='move',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'github',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node._id,
                'name': 'new.txt',
                'sizeInt': 220,
                'size': 220
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 220

    def test_add_log_updates_cache_copy(self):
        ''' Testing that file copies retain sizes on both source and destination nodes '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 250

        payload = self.build_payload_with_dest(
            action='copy',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node2._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 250

        self.node2.reload()
        assert self.node2.storage_usage == 250

    def test_add_log_updates_cache_copy_multiversion(self):
        ''' Testing that file copies retain sizes on both source and destination nodes '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        self.file2.create_version(self.user, {
            'object': '06d80f',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 275,
            'size': 275,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 525

        payload = self.build_payload_with_dest(
            action='copy',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node2._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 525

        self.node2.reload()
        assert self.node2.storage_usage == 525

    def test_add_log_updates_cache_copy_same_node(self):
        ''' Testing that a new copy is created and the size is added to the node '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        assert self.node.storage_usage == 250

        payload = self.build_payload_with_dest(
            action='copy',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 500

    def test_add_log_updates_cache_copy_same_node_multiversion(self):
        ''' Testing that a new copy is created and the size is added to the node '''
        self.configure_osf_addon()
        url = self.node.api_url_for('create_waterbutler_log')
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        self.file2.create_version(self.user, {
            'object': '06d80f',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 275,
            'size': 275,
            'contentType': 'img/png'
        }).save()


        assert self.node.storage_usage == 525

        payload = self.build_payload_with_dest(
            action='copy',
            source={
                'materialized': 'lollipop',
                'kind': 'file',
                'nid': self.node._id,
                'provider': 'osfstorage',
                'name': 'new.txt',
                'path': '/lollipop'
            },
            destination={
                'path': '/lollipop',
                'materialized': 'lollipop',
                'kind': 'file',
                'provider': 'osfstorage',
                'nid': self.node._id,
                'name': 'new.txt',
            },
        )
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 1050

    def test_add_log_updates_cache_delete(self):
        from addons.osfstorage import settings as osfstorage_settings

        url = self.node.api_url_for('create_waterbutler_log')

        self.configure_osf_addon()
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 200,
            'size': 200,
            'contentType': 'img/png'
        }).save()

        self.node.reload()
        assert self.node.storage_usage == 200

        payload = self.build_payload(metadata={
            'materialized': '/lollipop',
            'kind': 'file',
            'path': '/lollipop',
            'nid': self.node._id,
        }, action='delete')
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 0

    def test_add_log_updates_cache_delete_multiversion(self):
        from addons.osfstorage import settings as osfstorage_settings

        url = self.node.api_url_for('create_waterbutler_log')

        self.configure_osf_addon()
        self.file2.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 200,
            'size': 200,
            'contentType': 'img/png'
        }).save()

        self.file2.create_version(self.user, {
            'object': '06d80f',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'sizeInt': 250,
            'size': 250,
            'contentType': 'img/png'
        }).save()

        self.node.reload()
        assert self.node.storage_usage == 450

        payload = self.build_payload(metadata={
            'materialized': '/lollipop',
            'kind': 'file',
            'path': '/lollipop',
            'nid': self.node._id,
        }, action='delete')
        self.app.put(url, json=payload, headers={'Content-Type': 'application/json'})

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self.node._id)
        assert storage_usage_cache.get(key) == 0

    def test_add_folder_osfstorage_log(self):
        self.configure_osf_addon()
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'folder', 'path': path})
        nlogs = self.node.logs.count()
        self.app.put(url, json=payload)
        self.node.reload()
        assert self.node.logs.count() == nlogs + 1
        assert ('urls' not in self.node.logs.filter(action='osf_storage_file_added')[0].params)


class TestCheckAuth(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_has_permission(self):
        assert views.check_resource_permissions(self.node, Auth(user=self.user), 'upload')

    def test_not_has_permission_read_public(self):
        self.node.is_public = True
        self.node.save()
        views.check_resource_permissions(self.node, Auth(), 'download')

    def test_not_has_permission_read_has_link(self):
        link = new_private_link('red-special', self.user, [self.node], anonymous=False)
        views.check_resource_permissions(self.node, Auth(private_key=link.key), 'download')

    def test_not_has_permission_logged_in(self):
        user2 = AuthUserFactory()
        assert not views.check_resource_permissions(self.node, Auth(user=user2), 'download')

    def test_not_has_permission_not_logged_in(self):
        assert not views.check_resource_permissions(self.node, Auth(), 'download')

    def test_has_permission_on_parent_node_upload_pass_if_registration(self):
        component_admin = AuthUserFactory()
        ProjectFactory(creator=component_admin, parent=self.node)
        registration = RegistrationFactory(project=self.node)

        component_registration = registration._nodes.first()
        assert not component_registration.has_permission(self.user, WRITE)
        assert views.check_resource_permissions(component_registration, Auth(user=self.user), 'upload')

    def test_has_permission_on_parent_node_metadata_pass_if_registration(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, parent=self.node, is_public=False)

        component_registration = RegistrationFactory(project=component, creator=component_admin)

        assert not component_registration.has_permission(self.user, READ)
        assert views.check_resource_permissions(component_registration, Auth(user=self.user), 'metadata')

    def test_has_permission_on_parent_node_upload_fail_if_not_registration(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, parent=self.node)

        assert not component.has_permission(self.user, WRITE)
        assert not views.check_resource_permissions(component, Auth(user=self.user), 'upload')

    def test_has_permission_on_parent_node_copyfrom(self):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)

        assert not component.has_permission(self.user, WRITE)
        assert views.check_resource_permissions(component, Auth(user=self.user), 'copyfrom')


class TestCheckOAuth(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_private_not_authenticated(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=False)
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        with pytest.raises(HTTPError) as exc_info:
           views.authenticate_via_oauth_bearer_token(component, 'download')
        assert exc_info.value.code == 403

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_private_no_scope_forbidden(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                            attributes={'accessTokenScope': {}})
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        with pytest.raises(HTTPError) as exc_info:
             views.authenticate_via_oauth_bearer_token(component, 'download')
        assert exc_info.value.code == 403

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_public_irrelevant_scope_allowed(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(
            creator=component_admin,
            is_public=True,
            parent=self.node
        )
        mock_cas_response = cas.CasResponse(
            authenticated=True,
            status=None,
            user=self.user._id,
            attributes={'accessTokenScope': {'osf.users.all_read'}}
        )
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        assert views.authenticate_via_oauth_bearer_token(component, 'download')

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_private_irrelevant_scope_forbidden(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.users.all_read'}})
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        with pytest.raises(HTTPError) as exc_info:
            views.authenticate_via_oauth_bearer_token(component, 'download')
        assert exc_info.value.code == 403

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_decommissioned_scope_no_error(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {
                                       'decommissioned.scope+write',
                                       'osf.nodes.data_read',
                                   }})
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        assert views.authenticate_via_oauth_bearer_token(component, 'download')

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_write_scope_read_action(self, mock_get_client, mock_parse_auth_header):
        component_admin = AuthUserFactory()
        component = ProjectFactory(creator=component_admin, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.nodes.data_write'}})
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert not component.has_permission(self.user, WRITE)
        assert views.authenticate_via_oauth_bearer_token(component, 'download')

    @mock.patch('framework.auth.cas.parse_auth_header')
    @mock.patch('framework.auth.cas.get_client')
    def test_has_permission_read_scope_write_action_forbidden(self, mock_get_client, mock_parse_auth_header):
        component = ProjectFactory(creator=self.user, is_public=False, parent=self.node)
        mock_cas_response = cas.CasResponse(authenticated=True, status=None, user=self.user._id,
                                   attributes={'accessTokenScope': {'osf.nodes.data_read'}})
        mock_get_client.return_value.profile.return_value = mock_cas_response

        assert component.has_permission(self.user, WRITE)
        with pytest.raises(HTTPError) as exc_info:
            views.authenticate_via_oauth_bearer_token(component, 'upload')
        assert exc_info.value.code == 403


def assert_urls_equal(url1, url2):
    furl1 = furl(url1)
    furl2 = furl(url2)
    for attr in ['scheme', 'host', 'port']:
        setattr(furl1, attr, None)
        setattr(furl2, attr, None)
    # Note: furl params are ordered and cause trouble
    assert dict(furl1.args) == dict(furl2.args)
    furl1.set(args={})
    furl2.set(args={})
    assert furl1 == furl2


def mock_touch(self, bearer, version=None, revision=None, **kwargs):
    if version:
        if self.versions:
            try:
                return self.versions[int(version) - 1]
            except (IndexError, ValueError):
                return None
        else:
            return None
    return file_models.FileVersion()


@mock.patch('addons.github.models.GithubFileNode.touch', mock_touch)
@mock.patch('addons.github.models.GitHubClient.repo', mock.Mock(side_effect=ApiError))
class TestAddonFileViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.user.add_addon('github')
        self.project.add_addon('github', auth=Auth(self.user))

        self.user_addon = self.user.get_addon('github')
        self.node_addon = self.project.get_addon('github')
        self.oauth = GitHubAccountFactory()
        self.oauth.save()

        self.user.external_accounts.add(self.oauth)
        self.user.save()

        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth
        self.node_addon.repo = 'Truth'
        self.node_addon.user = 'E'
        self.node_addon.save()

        self.user_addon.oauth_grants[self.project._id] = {self.oauth._id: []}
        self.user_addon.save()

    def set_sentry(status):
        def wrapper(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                enabled, sentry.enabled = sentry.enabled, status
                func(*args, **kwargs)
                sentry.enabled = enabled

            return wrapped

        return wrapper

    with_sentry = set_sentry(True)

    def get_test_file(self):
        version = file_models.FileVersion(identifier='1')
        version.save()
        ret = GithubFile(
            name='Test',
            target=self.project,
            path='/test/Test',
            materialized_path='/test/Test',
        )
        ret.save()
        ret.add_version(version)
        return ret

    def get_second_test_file(self):
        version = file_models.FileVersion(identifier='1')
        version.save()
        ret = GithubFile(
            name='Test2',
            target=self.project,
            path='/test/Test2',
            materialized_path='/test/Test2',
        )
        ret.save()
        ret.add_version(version)
        return ret

    def get_uppercased_ext_test_file(self):
        version = file_models.FileVersion(identifier='1')
        version.save()
        ret = GithubFile(
            name='Test2.pdf',
            target=self.project,
            path='/test/Test2',
            materialized_path='/test/Test2',
        )
        ret.save()
        ret.add_version(version)
        return ret

    def get_ext_test_file(self):
        version = file_models.FileVersion(identifier='1')
        version.save()
        ret = GithubFile(
            name='Test2.pdf',
            target=self.project,
            path='/test/Test2',
            materialized_path='/test/Test2',
        )
        ret.save()
        ret.add_version(version)
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
                'profile_image': '',
                'external': '',
                'archived_from': '',
            },
            'sizeInt': '',
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

        assert resp.status_code == 302
        assert resp.location == f'/{guid._id}/'

    def test_action_download_redirects_to_download_with_param(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get(f'/{guid._id}/?action=download', auth=self.user.auth)

        assert resp.status_code == 302
        location = furl(resp.location)
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(action='download', direct=None, version=''))

    def test_action_download_redirects_to_download_with_path(self):
        file_node = self.get_uppercased_ext_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get(f'/{guid._id}/download?format=pdf', auth=self.user.auth)

        assert resp.status_code == 302
        location = furl(resp.location)
        assert location.url == file_node.generate_waterbutler_url(format='pdf', action='download', direct=None, version='')


    def test_action_download_redirects_to_download_with_path_uppercase(self):
        file_node = self.get_uppercased_ext_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get(f'/{guid._id}/download?format=pdf', auth=self.user.auth)

        assert resp.status_code == 302
        location = furl(resp.location)
        assert location.url == file_node.generate_waterbutler_url( format='pdf', action='download', direct=None, version='')

    def test_action_download_redirects_to_download_with_version(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.get(f'/{guid._id}/?action=download&revision=1', auth=self.user.auth)

        assert resp.status_code == 302
        location = furl(resp.location)
        # Note: version is added but us but all other url params are added as well
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(action='download', direct=None, revision=1, version=''))

    @mock.patch('website.views.stream_emberapp')
    @pytest.mark.enable_bookmark_creation
    def test_action_view_calls_view_file(self, mock_ember):
        self.user.reload()
        self.project.reload()

        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        with override_flag(features.EMBER_FILE_PROJECT_DETAIL, active=True):
            self.app.get(f'/{guid._id}/?action=view', auth=self.user.auth)

        args, kwargs = mock_ember.call_args
        assert kwargs == {}
        assert args[0] == EXTERNAL_EMBER_APPS['ember_osf_web']['server']
        assert args[1] == EXTERNAL_EMBER_APPS['ember_osf_web']['path'].rstrip('/')

    @mock.patch('website.views.stream_emberapp')
    @pytest.mark.enable_bookmark_creation
    def test_no_action_calls_view_file(self, mock_ember):
        self.user.reload()
        self.project.reload()

        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        with override_flag(features.EMBER_FILE_PROJECT_DETAIL, active=True):
            self.app.get(f'/{guid._id}/', auth=self.user.auth)

        args, kwargs = mock_ember.call_args
        assert kwargs == {}
        assert args[0] == EXTERNAL_EMBER_APPS['ember_osf_web']['server']
        assert args[1] == EXTERNAL_EMBER_APPS['ember_osf_web']['path'].rstrip('/')

    def test_download_create_guid(self):
        file_node = self.get_test_file()
        assert file_node.get_guid() is None

        self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=file_node.path.strip('/'),
                provider='github',
            ),
            auth=self.user.auth
        )

        assert file_node.get_guid()

    @pytest.mark.enable_bookmark_creation
    def test_view_file_does_not_delete_file_when_requesting_invalid_version(self):
        with mock.patch('addons.github.models.NodeSettings.is_private',
                        new_callable=mock.PropertyMock) as mock_is_private:
            mock_is_private.return_value = False

            file_node = self.get_test_file()
            assert file_node.get_guid() is None

            url = self.project.web_url_for(
                'addon_view_or_download_file',
                path=file_node.path.strip('/'),
                provider='github',
            )
            # First view generated GUID
            self.app.get(url, auth=self.user.auth)

            self.app.get(url + '?version=invalid', auth=self.user.auth, )

            assert BaseFileNode.load(file_node._id) is not None
            assert TrashedFileNode.load(file_node._id) is None

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

        )

        assert resp.status_code == 401

    def test_nonstorage_addons_raise(self):
        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path='sillywiki',
                provider='wiki',
                action='download'
            ),
            auth=self.user.auth,

        )

        assert resp.status_code == 400

    @mock.patch('website.views.stream_emberapp')
    def test_head_returns_url_and_redriect(self, mock_ember):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        with override_flag(features.EMBER_FILE_PROJECT_DETAIL, active=True):
            resp = self.app.head(f'/{guid._id}/', auth=self.user.auth)
        assert resp.status_code == 200

        args, kwargs = mock_ember.call_args
        assert kwargs == {}
        assert args[0] == EXTERNAL_EMBER_APPS['ember_osf_web']['server']
        assert args[1] == EXTERNAL_EMBER_APPS['ember_osf_web']['path'].rstrip('/')


    def test_head_returns_url_with_version_and_redirect(self):
        file_node = self.get_test_file()
        guid = file_node.get_guid(create=True)

        resp = self.app.head(f'/{guid._id}/?revision=1&foo=bar', auth=self.user.auth)
        location = furl(resp.location)
        # Note: version is added but us but all other url params are added as well
        assert resp.status_code == 302
        assert_urls_equal(location.url, file_node.generate_waterbutler_url(direct=None, revision=1, version='', foo='bar'))

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

        )

        assert resp.status_code == 400

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
        )

        assert resp.status_code == 401

    def test_resolve_folder_raise(self):
        folder = OsfStorageFolder(
            name='folder',
            target=self.project,
            path='/test/folder/',
            materialized_path='/test/folder/',
        )
        folder.save()
        resp = self.app.get(
            self.project.web_url_for(
                'addon_view_or_download_file',
                path=folder._id,
                provider='osfstorage',
            ),
            auth=self.user.auth,

        )

        assert resp.status_code == 400

    def test_delete_action_creates_trashed_file_node(self):
        file_node = self.get_test_file()
        payload = {
            'provider': file_node.provider,
            'metadata': {
                'path': '/test/Test',
                'materialized': '/test/Test'
            }
        }
        views.addon_delete_file_node(self=None, target=self.project, user=self.user, event_type='file_removed', payload=payload)
        assert not GithubFileNode.load(file_node._id)
        assert TrashedFileNode.load(file_node._id)

    def test_delete_action_for_folder_deletes_subfolders_and_creates_trashed_file_nodes(self):
        file_node = self.get_test_file()
        subfolder = GithubFolder(
            name='folder',
            target=self.project,
            path='/test/folder/',
            materialized_path='/test/folder/',
        )
        subfolder.save()
        payload = {
            'provider': file_node.provider,
            'metadata': {
                'path': '/test/',
                'materialized': '/test/'
            }
        }
        views.addon_delete_file_node(self=None, target=self.project, user=self.user, event_type='file_removed', payload=payload)
        assert not GithubFileNode.load(subfolder._id)
        assert TrashedFileNode.load(file_node._id)

    @mock.patch('website.archiver.tasks.archive')
    def test_archived_from_url(self, mock_archive):
        file_node = self.get_test_file()
        second_file_node = self.get_second_test_file()
        file_node.copied_from = second_file_node

        registered_node = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(self.user),
            draft_registration=DraftRegistrationFactory(branched_from=self.project),
        )

        archived_from_url = views.get_archived_from_url(registered_node, file_node)
        view_url = self.project.web_url_for('addon_view_or_download_file', provider=file_node.provider, path=file_node.copied_from._id)
        assert archived_from_url
        assert_urls_equal(archived_from_url, view_url)

    @mock.patch('website.archiver.tasks.archive')
    def test_archived_from_url_without_copied_from(self, mock_archive):
        file_node = self.get_test_file()

        registered_node = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(self.user),
            draft_registration=DraftRegistrationFactory(branched_from=self.project),
        )
        archived_from_url = views.get_archived_from_url(registered_node, file_node)
        assert not archived_from_url

    @mock.patch('website.archiver.tasks.archive')
    def test_copied_from_id_trashed(self, mock_archive):
        file_node = self.get_test_file()
        second_file_node = self.get_second_test_file()
        file_node.copied_from = second_file_node
        self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(self.user),
            draft_registration=DraftRegistrationFactory(branched_from=self.project),
        )
        trashed_node = second_file_node.delete()
        assert not trashed_node.copied_from

    @mock.patch('website.archiver.tasks.archive')
    def test_missing_modified_date_in_file_data(self, mock_archive):
        file_node = self.get_test_file()
        file_data = {
            'name': 'Test File Update',
            'materialized': file_node.materialized_path,
            'modified': None
        }
        file_node.update(revision=None, data=file_data)
        assert len(file_node.history) == 1
        assert file_node.history[0] == file_data

    @mock.patch('website.archiver.tasks.archive')
    def test_missing_modified_date_in_file_history(self, mock_archive):
        file_node = self.get_test_file()
        file_node.history.append({'modified': None})
        file_data = {
            'name': 'Test File Update',
            'materialized': file_node.materialized_path,
            'modified': None
        }
        file_node.update(revision=None, data=file_data)
        assert len(file_node.history) == 2
        assert file_node.history[1] == file_data

    @with_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_message')
    def test_update_logs_to_sentry_when_called_with_disordered_metadata(self, mock_capture: Mock, mock_set_context: Mock):
        file_node = self.get_test_file()
        file_node.history.append({'modified': parse_date(
                '2017-08-22T13:54:32.100900',
                ignoretz=True,
                default=timezone.now()  # Just incase nothing can be parsed
            )})
        data = {
            'name': 'a name',
            'materialized': 'materialized',
            'modified': '2016-08-22T13:54:32.100900'
        }
        file_node.update(revision=None, user=None, data=data)
        mock_set_context.return_value.__enter__.return_value.set_extra.assert_called_once_with('session', {})
        mock_capture.assert_called_with(
            'update() receives metatdata older than the newest entry in file history.',
            level='error',
        )

class TestLegacyViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.path = 'mercury.png'
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = self.project.get_addon('osfstorage')
        file_record = self.node_addon.get_root().append_file(self.path)
        self.expected_path = file_record._id
        self.node_addon.save()
        file_record.save()

    def test_view_file_redirect(self):
        url = f'/{self.project._id}/osffiles/{self.path}/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.expected_path,
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_redirect(self):
        url = f'/{self.project._id}/osffiles/{self.path}/download/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_download_file_version_redirect(self):
        url = f'/{self.project._id}/osffiles/{self.path}/version/3/download/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            version=3,
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_redirect(self):
        url = f'/api/v1/project/{self.project._id}/osffiles/{self.path}/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_api_download_file_version_redirect(self):
        url = f'/api/v1/project/{self.project._id}/osffiles/{self.path}/version/3/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            version=3,
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_no_provider_name(self):
        url = f'/{self.project._id}/files/{self.path}'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.expected_path,
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    @pytest.mark.enable_bookmark_creation
    def test_action_as_param(self):
        url = f'/{self.project._id}/osfstorage/files/{self.path}/?action=download'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.expected_path,
            action='download',
            provider='osfstorage',
        )
        assert_urls_equal(res.location, expected_url)

    def test_other_addon_redirect(self):
        url = f'/project/{self.project._id}/mycooladdon/files/{self.path}/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            action='view',
            path=self.path,
            provider='mycooladdon',
        )
        assert_urls_equal(res.location, expected_url)

    def test_other_addon_redirect_download(self):
        url = f'/project/{self.project._id}/mycooladdon/files/{self.path}/download/'
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 301
        expected_url = self.project.web_url_for(
            'addon_view_or_download_file',
            path=self.path,
            action='download',
            provider='mycooladdon',
        )
        assert_urls_equal(res.location, expected_url)

class TestViewUtils(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user)
        self.session = SessionStore()
        self.session['auth_user_id'] = self.user._id
        self.session.create()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session.session_key)
        self.configure_addon()
        self.JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))
        self.mock_api_credentials_are_valid = mock.patch('addons.github.api.GitHubClient.check_authorization', return_value=True)
        self.mock_api_credentials_are_valid.start()

    def configure_addon(self):
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')
        self.oauth_settings = GitHubAccountFactory(display_name='john')
        self.oauth_settings.save()
        self.user.external_accounts.add(self.oauth_settings)
        self.user.save()
        self.node.add_addon('github', self.auth_obj)
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = 'john'
        self.node_addon.repo = 'youre-my-best-friend'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.oauth_settings
        self.node_addon.save()
        self.user_addon.oauth_grants[self.node._id] = {self.oauth_settings._id: []}
        self.user_addon.save()

    @mock.patch('addons.github.models.NodeSettings.get_folders', return_value=[])
    def test_serialize_addons(self, mock_folders):
        addon_dicts = serialize_addons(self.node, self.auth_obj)

        enabled_addons = [addon for addon in addon_dicts if addon['enabled']]
        assert len(enabled_addons) == 2
        assert enabled_addons[0]['short_name'] == 'github'
        assert enabled_addons[1]['short_name'] == 'osfstorage'

        default_addons = [addon for addon in addon_dicts if addon['default']]
        assert len(default_addons) == 1
        assert default_addons[0]['short_name'] == 'osfstorage'

    @mock.patch('addons.github.models.NodeSettings.get_folders', return_value=[])
    def test_include_template_json(self, mock_folders):
        """ Some addons (github, gitlab) need more specialized template infomation so we want to
        ensure we get those extra variables that when the addon is enabled.
        """
        addon_dicts = serialize_addons(self.node, self.auth_obj)

        enabled_addons = [addon for addon in addon_dicts if addon['enabled']]
        assert len(enabled_addons) == 2
        assert enabled_addons[1]['short_name'] == 'osfstorage'
        assert enabled_addons[0]['short_name'] == 'github'
        assert 'node_has_auth' in enabled_addons[0]
        assert 'valid_credentials' in enabled_addons[0]

    @mock.patch('addons.github.models.NodeSettings.get_folders', return_value=[])
    def test_collect_node_config_js(self, mock_folders):

        addon_dicts = serialize_addons(self.node, self.auth_obj)

        asset_paths = collect_node_config_js(addon_dicts)

        # Default addons should be in addon dicts, but they have no js assets because you can't
        # connect/disconnect from them, think osfstorage, there's no node-cfg for that.
        default_addons = [addon['short_name'] for addon in addon_dicts if addon['default']]
        assert not any(f'/{addon}/' in asset_paths for addon in default_addons)
