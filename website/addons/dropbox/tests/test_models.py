# -*- coding: utf-8 -*-
import os

from nose.tools import *  # PEP8 asserts
from slugify import slugify

from framework.auth.decorators import Auth
from website.addons.dropbox.model import (
    DropboxUserSettings, DropboxNodeSettings, DropboxFile
)
from tests.base import OsfTestCase, fake
from tests.factories import UserFactory, ProjectFactory
from website.addons.dropbox.tests.utils import MockDropbox
from website.addons.dropbox.tests.factories import (
    DropboxUserSettingsFactory, DropboxNodeSettingsFactory,
    DropboxFileFactory
)
from website.app import init_app
from website.util import web_url_for

app = init_app(set_backends=False, routes=True)


class TestUserSettingsModel(OsfTestCase):

    def setUp(self):
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

        old_logs = node_settings.owner.logs

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
        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()
        self.user_settings = self.user.get_addon('dropbox')
        self.project = ProjectFactory()
        self.node_settings = DropboxNodeSettingsFactory(
            user_settings=self.user_settings,
            owner=self.project
        )

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


class TestNodeSettingsCallbacks(OsfTestCase):

    def setUp(self):
        # Create node settings with auth
        self.user_settings = DropboxUserSettingsFactory(access_token='123abc')
        self.node_settings = DropboxNodeSettingsFactory(user_settings=self.user_settings,
            folder='')

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

    def test_after_remove_authorized_dropbox_user(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)


class TestDropboxGuidFile(OsfTestCase):

    def test_verbose_url(self):
        project = ProjectFactory()
        file_obj = DropboxFile(node=project, path='foo.txt')
        file_obj.save()
        file_url = file_obj.url(guid=False)

        url = web_url_for('dropbox_view_file',
            pid=project._primary_key, path=file_obj.path, rev='')
        assert_equal(url, file_url)

    def test_guid_url(self):
        file_obj = DropboxFileFactory()
        result = file_obj.url(guid=True, rev='123')
        assert_equal(result, '/{guid}/?rev=123'.format(guid=file_obj._primary_key))

    def test_cache_file_name(self):
        project = ProjectFactory()
        path = 'My Project/foo.txt'
        file_obj = DropboxFile(node=project, path=path)
        mock_client = MockDropbox()
        file_obj.update_metadata(client=mock_client)
        file_obj.save()

        result = file_obj.get_cache_filename(client=mock_client)
        assert_equal(result, "{0}_{1}.html".format(slugify(file_obj.path),
            file_obj.metadata['rev']))

    def test_download_url(self):
        file_obj = DropboxFileFactory()
        dl_url = file_obj.download_url(guid=False)
        expected = file_obj.node.web_url_for('dropbox_download', path=file_obj.path,
            rev='', _absolute=True)
        assert_equal(dl_url, expected)

    def test_download_url_guid(self):
        file_obj = DropboxFileFactory()
        dl_url = file_obj.download_url(guid=True, rev='123')
        expected = os.path.join('/', file_obj._primary_key, 'download/') + "?rev=123"
        assert_equal(dl_url, expected)

    def test_update_metadata(self):
        client = MockDropbox()
        file_obj = DropboxFileFactory(metadata=None)
        file_obj.update_metadata(client=client)
        file_obj.save()
        assert_equal(file_obj.metadata, client.metadata(file_obj.path, list=False))
