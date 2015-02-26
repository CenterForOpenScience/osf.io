# -*- coding: utf-8 -*-
import time
from datetime import datetime
from nose.tools import *  # noqa (PEP8 asserts)

import mock
from dateutil import relativedelta

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.base import exceptions

from website.addons.googledrive.client import GoogleAuthClient
from website.addons.googledrive.model import (
    GoogleDriveUserSettings,
    GoogleDriveNodeSettings,
    GoogleDriveOAuthSettings,
    GoogleDriveGuidFile,
)
from website.addons.googledrive.tests.factories import (
    GoogleDriveNodeSettingsFactory,
    GoogleDriveUserSettingsFactory,
    GoogleDriveOAuthSettingsFactory,
)


class TestFileGuid(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('googledrive')

        self.node_addon.folder_id = 'Lulz'
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()

    def test_provider(self):
        assert_equal('googledrive', GoogleDriveGuidFile().provider)

    def test_correct_path(self):
        guid = GoogleDriveGuidFile(node=self.project, path='/baz/foo/bar')

        assert_equals(guid.path, '/baz/foo/bar')
        assert_equals(guid.waterbutler_path, '/foo/bar')

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'revisionId': 'Ricksy'
                }
            }
        }

        guid = GoogleDriveGuidFile(node=self.project, path='/foo/bar')

        guid.enrich()
        assert_equals('Ricksy', guid.unique_identifier)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created)
        assert_equal(guid.path, '/baz/foo/bar')
        assert_equal(guid.waterbutler_path, '/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)

    def test_node_addon_get_or_create_finds_changed(self):
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()
        self.node_addon.reload()

        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')

        self.node_addon.folder_path = 'baz/foo'
        self.node_addon.save()
        self.node_addon.reload()
        guid2, created2 = self.node_addon.find_or_create_file_guid('/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)

    def test_node_addon_get_or_create_finds_changed_root(self):
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()
        self.node_addon.reload()

        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')

        self.node_addon.folder_path = '/'
        self.node_addon.save()
        self.node_addon.reload()
        guid2, created2 = self.node_addon.find_or_create_file_guid('/baz/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestGoogleDriveUserSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveUserSettingsModel, self).setUp()
        self.user = UserFactory()

    def test_fields(self):
        user_settings = GoogleDriveUserSettingsFactory()
        retrieved = GoogleDriveUserSettings.load(user_settings._primary_key)

        assert_true(retrieved.owner)
        assert_true(retrieved.username)
        assert_true(retrieved.expires_at)
        assert_true(retrieved.access_token)

    def test_has_auth(self):
        user_settings = GoogleDriveUserSettingsFactory(access_token=None)
        assert_false(user_settings.has_auth)
        user_settings.access_token = '12345'
        user_settings.save()
        assert_true(user_settings.has_auth)

    @mock.patch.object(GoogleDriveOAuthSettings, '_needs_refresh', new_callable=mock.PropertyMock)
    def test_access_token_checks(self, mock_needs_refresh):
        mock_needs_refresh.return_value = False
        user_settings = GoogleDriveUserSettingsFactory()

        user_settings.access_token

        assert_true(mock_needs_refresh.called_once)

    @mock.patch.object(GoogleAuthClient, 'refresh')
    @mock.patch.object(GoogleDriveOAuthSettings, '_needs_refresh', new_callable=mock.PropertyMock)
    def test_access_token_refreshes(self, mock_needs_refresh, mock_refresh):
        mock_refresh.return_value = {
            'access_token': 'abc',
            'refresh_token': '123',
            'expires_at': time.time(),
        }
        user_settings = GoogleDriveUserSettingsFactory()
        user_settings.expires_at = datetime.now()
        user_settings.access_token
        assert_true(mock_refresh.called_once)

    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_access_token_refreshes_timeout(self, mock_refresh):
        mock_refresh.return_value = {
            'access_token': 'abc',
            'refresh_token': '123',
            'expires_at': time.time(),
        }
        user_settings = GoogleDriveUserSettingsFactory()
        user_settings.expires_at = (datetime.utcnow() + relativedelta.relativedelta(seconds=5))

        user_settings.access_token

        assert_true(mock_refresh.called_once)

    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_access_token_refreshes_timeout_longer(self, mock_refresh):
        mock_refresh.return_value = {
            'access_token': 'abc',
            'refresh_token': '123',
            'expires_at': time.time(),
        }
        user_settings = GoogleDriveUserSettingsFactory()
        user_settings.expires_at = datetime.utcnow() + relativedelta.relativedelta(minutes=4)
        user_settings.access_token
        assert_true(mock_refresh.called_once)

    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_access_token_doesnt_refresh(self, mock_refresh):
        user_settings = GoogleDriveUserSettingsFactory()
        user_settings.save()
        user_settings.access_token
        assert_false(mock_refresh.called)

    def test_clear_clears_associated_node_settings(self):
        node_settings = GoogleDriveNodeSettingsFactory.build()
        user_settings = GoogleDriveUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()
        user_settings.clear()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_is(node_settings.folder_id, None)
        assert_is(node_settings.user_settings, None)

    def test_clear(self):
        node_settings = GoogleDriveNodeSettingsFactory.build()
        user_settings = GoogleDriveUserSettingsFactory(access_token='abcde')
        node_settings.user_settings = user_settings
        node_settings.save()

        assert_true(user_settings.access_token)
        user_settings.clear()
        user_settings.save()
        assert_false(user_settings.access_token)

    def test_delete(self):
        user_settings = GoogleDriveUserSettingsFactory()
        assert_true(user_settings.has_auth)
        user_settings.delete()
        user_settings.save()
        assert_false(user_settings.access_token)
        assert_true(user_settings.deleted)

    def test_delete_clears_associated_node_settings(self):
        node_settings = GoogleDriveNodeSettingsFactory.build()
        user_settings = GoogleDriveUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        user_settings.delete()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_false(node_settings.deleted)
        assert_is(node_settings.folder_id, None)
        assert_is(node_settings.user_settings, None)


class TestGoogleDriveNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveNodeSettingsModel, self).setUp()
        self.user = UserFactory()
        self.user.add_addon('googledrive')
        self.user.save()
        self.user_settings = self.user.get_addon('googledrive')
        oauth_settings = GoogleDriveOAuthSettingsFactory()
        oauth_settings.save()
        self.user_settings.oauth_settings = oauth_settings
        self.user_settings.save()
        self.project = ProjectFactory()
        self.node_settings = GoogleDriveNodeSettingsFactory(
            user_settings=self.user_settings,
            owner=self.project,
        )

    def test_fields(self):
        node_settings = GoogleDriveNodeSettings(user_settings=self.user_settings)
        node_settings.save()

        assert_true(node_settings.user_settings)
        assert_true(hasattr(node_settings, 'folder_id'))
        assert_true(hasattr(node_settings, 'folder_path'))
        assert_true(hasattr(node_settings, 'folder_name'))
        assert_equal(node_settings.user_settings.owner, self.user)

    def test_folder_defaults_to_none(self):
        node_settings = GoogleDriveNodeSettings(user_settings=self.user_settings)
        node_settings.save()

        assert_is_none(node_settings.folder_id)
        assert_is_none(node_settings.folder_path)

    def test_has_auth(self):
        settings = GoogleDriveNodeSettings(user_settings=self.user_settings)
        settings.user_settings.access_token = None
        settings.save()

        assert_false(settings.has_auth)

        settings.user_settings.access_token = '123abc'
        settings.user_settings.save()

        assert_true(settings.has_auth)

    # TODO use this test if delete function is used in googledrive/model
    # def test_delete(self):
    #     assert_true(self.node_settings.user_settings)
    #     assert_true(self.node_settings.folder)
    #     old_logs = self.project.logs
    #     self.node_settings.delete()
    #     self.node_settings.save()
    #     assert_is(self.node_settings.user_settings, None)
    #     assert_is(self.node_settings.folder, None)
    #     assert_true(self.node_settings.deleted)
    #     assert_equal(self.project.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.folder_id)
        assert_true(self.node_settings.user_settings)

        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()

        assert_is(self.node_settings.folder_id, None)
        assert_is(self.node_settings.user_settings, None)

        last_log = self.project.logs[-1]
        params = last_log.params

        assert_in('node', params)
        assert_in('folder', params)
        assert_in('project', params)
        assert_equal(last_log.action, 'googledrive_node_deauthorized')

    def test_set_folder(self):
        folder_name = {
            'id': '1234',
            'name': 'freddie',
            'path': 'queen/freddie',
        }

        self.node_settings.set_folder(folder_name, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_name, folder_name['name'])
        # Log was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'googledrive_folder_selected')

    def test_set_user_auth(self):
        node_settings = GoogleDriveNodeSettingsFactory()
        user_settings = GoogleDriveUserSettingsFactory()

        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        log_params = last_log.params

        assert_equal(last_log.user, user_settings.owner)
        assert_equal(log_params['folder'], node_settings.folder_path)
        assert_equal(last_log.action, 'googledrive_node_authorized')
        assert_equal(log_params['node'], node_settings.owner._primary_key)

    def test_serialize_credentials(self):
        self.user_settings.access_token = 'secret'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()
        expected = {'token': self.node_settings.user_settings.access_token}
        assert_equal(credentials, expected)

    def test_serialize_credentials_not_authorized(self):
        self.node_settings.user_settings = None
        self.node_settings.save()

        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        self.node_settings.folder_path = 'camera uploads/pizza.nii'
        self.node_settings.save()

        settings = self.node_settings.serialize_waterbutler_settings()

        expected = {
            'folder': {
                'id': '12345',
                'name': 'pizza.nii',
                'path': 'camera uploads/pizza.nii',
            }
        }

        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder_id = None
        self.node_settings.save()

        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()

    def test_create_log(self):
        action = 'file_added'
        path = '12345/camera uploads/pizza.nii'

        nlog = len(self.project.logs)
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': path},
        )

        self.project.reload()

        assert_equal(len(self.project.logs), nlog + 1)
        assert_equal(
            self.project.logs[-1].action,
            'googledrive_{0}'.format(action),
        )
        assert_equal(self.project.logs[-1].params['path'], path)


class TestNodeSettingsCallbacks(OsfTestCase):

    def setUp(self):
        super(TestNodeSettingsCallbacks, self).setUp()
        # Create node settings with auth
        self.user_settings = GoogleDriveUserSettingsFactory(access_token='123abc', username='name/email')
        self.node_settings = GoogleDriveNodeSettingsFactory(
            user_settings=self.user_settings,
            folder='',
        )

        self.project = self.node_settings.owner
        self.user = self.user_settings.owner

    def test_after_fork_by_authorized_googledrive_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_googledrive_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=user,
            save=True
        )
        # need request context for url_for
        assert_is(clone.user_settings, None)

    def test_before_fork(self):
        node = ProjectFactory()
        message = self.node_settings.before_fork(node, self.user)
        assert_true(message)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.project.project_or_component, message)

    def test_after_remove_authorized_googledrive_user(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.folder_id is None)
        assert_true(self.node_settings.folder_path is None)
        assert_true(self.node_settings.user_settings is None)

    def test_does_not_get_copied_to_registrations(self):
        registration = self.project.register_node(
            schema=None,
            auth=Auth(user=self.project.creator),
            template='Template1',
            data='hodor'
        )
        assert_false(registration.has_addon('googledrive'))
