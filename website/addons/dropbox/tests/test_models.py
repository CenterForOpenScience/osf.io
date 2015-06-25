# -*- coding: utf-8 -*-
import os
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.addons.dropbox.model import (
    DropboxUserSettings, DropboxNodeSettings, DropboxFile
)
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.dropbox.tests.factories import (
    DropboxUserSettingsFactory, DropboxNodeSettingsFactory,
)
from website.addons.base import exceptions


class TestFileGuid(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('dropbox', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('dropbox')
        self.node_addon.folder = '/baz'
        self.node_addon.save()

    def test_provider(self):
        assert_equal('dropbox', DropboxFile().provider)

    def test_correct_path(self):
        guid = DropboxFile(node=self.project, path='baz/foo/bar')

        assert_equals(guid.path, 'baz/foo/bar')
        assert_equals(guid.waterbutler_path, '/foo/bar')

    def test_path_doesnt_crash_without_addon(self):
        guid = DropboxFile(node=self.project, path='baz/foo/bar')
        self.project.delete_addon('dropbox', Auth(self.user))

        assert_is(self.project.get_addon('dropbox'), None)

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

    def test_path_doesnt_crash_nonconfig_addon(self):
        guid = DropboxFile(node=self.project, path='baz/foo/bar')
        self.node_addon.folder = None
        self.node_addon.save()
        self.node_addon.reload()

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

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

        guid = DropboxFile(node=self.project, path='/foo/bar')

        guid.enrich()
        assert_equals('Ricksy', guid.unique_identifier)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created)
        assert_equal(guid.path, 'baz/foo/bar')
        assert_equal(guid.waterbutler_path, '/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)

    def test_node_addon_get_or_create_finds_changed(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')

        self.node_addon.folder = '/baz/foo'
        self.node_addon.save()
        self.node_addon.reload()
        guid2, created2 = self.node_addon.find_or_create_file_guid('/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestUserSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestUserSettingsModel, self).setUp()
        self.user = UserFactory()

    def test_fields(self):
        user_settings = DropboxUserSettings(
            access_token='12345',
            dropbox_id='abc',
            owner=self.user)
        user_settings.save()
        retrieved = DropboxUserSettings.load(user_settings._primary_key)
        assert_true(retrieved.access_token)
        assert_true(retrieved.dropbox_id)
        assert_true(retrieved.owner)

    def test_has_auth(self):
        user_settings = DropboxUserSettingsFactory(access_token=None)
        assert_false(user_settings.has_auth)
        user_settings.access_token = '12345'
        user_settings.save()
        assert_true(user_settings.has_auth)

    def test_clear_clears_associated_node_settings(self):
        node_settings = DropboxNodeSettingsFactory.build()
        user_settings = DropboxUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        user_settings.clear()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_is(node_settings.user_settings, None)
        assert_is(node_settings.folder, None)

    def test_clear(self):
        node_settings = DropboxNodeSettingsFactory.build()
        user_settings = DropboxUserSettingsFactory(access_token='abcde',
            dropbox_id='abc')
        node_settings.user_settings = user_settings
        node_settings.save()

        assert_true(user_settings.access_token)
        user_settings.clear()
        user_settings.save()
        assert_false(user_settings.access_token)
        assert_false(user_settings.dropbox_id)

    def test_delete(self):
        user_settings = DropboxUserSettingsFactory()
        assert_true(user_settings.has_auth)
        user_settings.delete()
        user_settings.save()
        assert_false(user_settings.access_token)
        assert_false(user_settings.dropbox_id)
        assert_true(user_settings.deleted)

    def test_delete_clears_associated_node_settings(self):
        node_settings = DropboxNodeSettingsFactory.build()
        user_settings = DropboxUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        user_settings.delete()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_is(node_settings.user_settings, None)
        assert_is(node_settings.folder, None)
        assert_false(node_settings.deleted)

    def test_to_json(self):
        user_settings = DropboxUserSettingsFactory()
        result = user_settings.to_json()
        assert_equal(result['has_auth'], user_settings.has_auth)


class TestDropboxNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestDropboxNodeSettingsModel, self).setUp()
        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()
        self.user_settings = self.user.get_addon('dropbox')
        self.project = ProjectFactory()
        self.node_settings = DropboxNodeSettingsFactory(
            user_settings=self.user_settings,
            owner=self.project
        )

    def test_complete_true(self):
        self.node_settings.user_settings.access_token = 'seems legit'

        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.node_settings.user_settings.access_token = 'seems legit'
        self.node_settings.folder = None

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_fields(self):
        node_settings = DropboxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'folder'))
        assert_true(hasattr(node_settings, 'registration_data'))

    def test_folder_defaults_to_none(self):
        node_settings = DropboxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder)

    def test_has_auth(self):
        settings = DropboxNodeSettings(user_settings=self.user_settings)
        settings.save()
        assert_false(settings.has_auth)

        settings.user_settings.access_token = '123abc'
        settings.user_settings.save()
        assert_true(settings.has_auth)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'dropbox')

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder)
        old_logs = self.project.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder, None)
        assert_true(self.node_settings.deleted)
        assert_equal(self.project.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder, None)

        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_node_deauthorized')
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)
        assert_in('folder', params)

    def test_set_folder(self):
        folder_name = 'queen/freddie'
        self.node_settings.set_folder(folder_name, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder, folder_name)
        # Log was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_folder_selected')

    def test_set_user_auth(self):
        node_settings = DropboxNodeSettingsFactory()
        user_settings = DropboxUserSettingsFactory()

        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, 'dropbox_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['folder'], node_settings.folder)
        assert_equal(log_params['node'], node_settings.owner._primary_key)
        assert_equal(last_log.user, user_settings.owner)

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
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'folder': self.node_settings.folder}
        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder = None
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()

    def test_create_log(self):
        action = 'file_added'
        path = 'pizza.nii'
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
            'dropbox_{0}'.format(action),
        )
        assert_equal(
            self.project.logs[-1].params['path'],
            path,
        )

    @mock.patch('website.archiver.tasks.archive.si')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=None,
            auth=Auth(user=self.project.creator),
            template='Template1',
            data='hodor'
        )
        assert_false(registration.has_addon('dropbox'))


class TestNodeSettingsCallbacks(OsfTestCase):

    def setUp(self):
        super(TestNodeSettingsCallbacks, self).setUp()
        # Create node settings with auth
        self.user_settings = DropboxUserSettingsFactory(access_token='123abc')
        self.node_settings = DropboxNodeSettingsFactory(
            user_settings=self.user_settings,
            folder='',
        )

        self.project = self.node_settings.owner
        self.user = self.user_settings.owner

    def test_after_fork_by_authorized_dropbox_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_dropbox_user(self):
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

    def test_after_remove_authorized_dropbox_user_self(self):
        auth = Auth(user=self.user_settings.owner)
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner, auth)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_remove_authorized_dropbox_user_not_self(self):
        message = self.node_settings.after_remove_contributor(
            node=self.project, removed=self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.folder is None)
