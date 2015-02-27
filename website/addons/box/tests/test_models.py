# -*- coding: utf-8 -*-
import os
import mock
from datetime import datetime

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.addons.box.model import (
    BoxUserSettings, BoxNodeSettings, BoxFile
)
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.box.tests.factories import (
    BoxOAuthSettings,
    BoxUserSettingsFactory, BoxNodeSettingsFactory,
)
from website.addons.base import exceptions


class TestFileGuid(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('box', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('box')

    def test_provider(self):
        assert_equal('box', BoxFile().provider)

    def test_correct_path(self):
        guid = BoxFile(node=self.project, path='1234567890/foo/bar')

        assert_equals(guid.path, '1234567890/foo/bar')
        assert_equals(guid.waterbutler_path, '/1234567890/foo/bar')

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier(self, mock_get):
        uid = '#!'
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'extra': {
                    'etag': uid
                },
            }
        }

        guid = BoxFile(node=self.project, path='1234567890/foo/bar')
        guid.enrich()
        assert_equals(uid, guid.unique_identifier)

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier_version(self, mock_get):
        uid = '#!'
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'extra': {},
                'version': uid
            }
        }

        guid = BoxFile(node=self.project, path='1234567890/foo/bar')
        guid.enrich()
        assert_equals(uid, guid.unique_identifier)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('1234567890/foo/bar')

        assert_true(created)
        assert_equal(guid.path, '1234567890/foo/bar')
        assert_equal(guid.waterbutler_path, '/1234567890/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestUserSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestUserSettingsModel, self).setUp()
        self.user = UserFactory()

    def test_fields(self):
        oauth_settings = BoxOAuthSettings(user_id='foo', username='bar', access_token='defined')
        oauth_settings.save()
        user_settings = BoxUserSettings(owner=self.user, oauth_settings=oauth_settings)

        user_settings.save()
        retrieved = BoxUserSettings.load(user_settings._id)

        assert_true(retrieved.owner)
        assert_true(retrieved.user_id)
        assert_true(retrieved.username)
        assert_true(retrieved.access_token)

    def test_has_auth(self):
        oauth_settings = BoxOAuthSettings(user_id='foo', username='bar')
        oauth_settings.save()

        user_settings = BoxUserSettingsFactory(oauth_settings=oauth_settings)

        assert_false(user_settings.has_auth)
        user_settings.access_token = '12345'
        user_settings.save()
        assert_true(user_settings.has_auth)

    @mock.patch('website.addons.box.model.requests')
    def test_clear_clears_associated_node_settings(self, mock_requests):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        user_settings.clear()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_is(node_settings.folder_id, None)
        assert_is(node_settings.user_settings, None)
        mock_requests.post.assert_called_once()

    @mock.patch('website.addons.box.model.requests')
    def test_clear(self, mock_requests):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        assert_true(user_settings.access_token)
        user_settings.clear()
        user_settings.save()

        assert_false(user_settings.user_id)
        assert_false(user_settings.access_token)
        mock_requests.post.assert_called_once()

    @mock.patch('website.addons.box.model.requests')
    def test_clear_wo_oauth_settings(self, mock_requests):
        user_settings = BoxUserSettingsFactory()
        user_settings.oauth_settings = None
        user_settings.save()
        node_settings = BoxNodeSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        assert_false(user_settings.oauth_settings)
        user_settings.clear()
        user_settings.save()

        assert_false(user_settings.user_id)
        assert_false(user_settings.access_token)
        assert_false(mock_requests.post.called)

    @mock.patch('website.addons.box.model.requests')
    def test_delete(self, mock_requests):
        user_settings = BoxUserSettingsFactory()
        assert_true(user_settings.has_auth)
        user_settings.delete()
        user_settings.save()

        assert_false(user_settings.user_id)
        assert_true(user_settings.deleted)
        assert_false(user_settings.access_token)
        mock_requests.post.assert_called_once()

    @mock.patch('website.addons.box.model.requests')
    def test_delete_clears_associated_node_settings(self, mock_requests):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()
        node_settings.user_settings = user_settings
        node_settings.save()

        user_settings.delete()
        user_settings.save()

        # Node settings no longer associated with user settings
        assert_false(node_settings.deleted)
        assert_is(node_settings.folder_id, None)
        mock_requests.post.assert_called_once()
        assert_is(node_settings.user_settings, None)


class TestBoxNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestBoxNodeSettingsModel, self).setUp()
        self.user = UserFactory()
        self.user.add_addon('box')
        self.user.save()
        self.oauth = BoxOAuthSettings(user_id='not sleep')
        self.oauth.save()

        self.user_settings = self.user.get_addon('box')
        self.user_settings.oauth_settings = self.oauth
        self.user_settings.save()
        self.project = ProjectFactory()
        self.node_settings = BoxNodeSettingsFactory(
            user_settings=self.user_settings,
            folder_id = '1234567890',
            owner=self.project
        )

    def test_fields(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'folder_id'))
        assert_true(hasattr(node_settings, 'user_settings'))

    def test_folder_defaults_to_none(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    def test_has_auth(self):
        settings = BoxNodeSettings(user_settings=self.user_settings, )
        settings.save()
        assert_false(settings.has_auth)

        settings.user_settings.access_token = '123abc'
        settings.user_settings.save()
        assert_true(settings.has_auth)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'box')

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        old_logs = self.project.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)
        assert_true(self.node_settings.deleted)
        assert_equal(self.project.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)
        assert_in('folder_id', params)

    def test_set_folder(self):
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'box_folder_selected')

    def test_set_user_auth(self):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()

        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, 'box_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['folder_id'], node_settings.folder_id)
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
        expected = {'folder': self.node_settings.folder_id}
        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder_id = None
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
            'box_{0}'.format(action),
        )
        assert_equal(
            self.project.logs[-1].params['path'],
            os.path.join(self.node_settings.folder_id, path),
        )


class TestNodeSettingsCallbacks(OsfTestCase):

    def setUp(self):
        super(TestNodeSettingsCallbacks, self).setUp()
        # Create node settings with auth
        self.user_settings = BoxUserSettingsFactory(access_token='123abc')
        self.node_settings = BoxNodeSettingsFactory(
            user_settings=self.user_settings,
        )

        self.project = self.node_settings.owner
        self.user = self.user_settings.owner

    def test_after_fork_by_authorized_box_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_box_user(self):
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

    def test_after_remove_authorized_box_user(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.folder_id is None)
