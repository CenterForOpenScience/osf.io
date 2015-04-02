# -*- coding: utf-8 -*-
import mock
import time
import datetime

from nose.tools import *  # noqa
from framework.auth import Auth
from website.addons.googledrive.client import GoogleDriveClient
from website.util import api_url_for, web_url_for
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.googledrive.tests.utils import mock_folders
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory


class TestGoogleDriveConfigViews(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveConfigViews, self).setUp()
        self.account = GoogleDriveAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        # self.user = AuthUserFactory()
        # self.user.add_addon('googledrive')
        self.user_settings = self.user.get_or_add_addon('googledrive')
        # self.user_settings = self.user.get_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()
        self.user_settings.save()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_list_googledrive_accounts_returns_accounts_single(self):
        url = api_url_for('list_googledrive_user_accounts', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['accounts']), 1)
        assert_equal(res.json['accounts'][0]['provider_id'], self.account.provider_id)
        assert_equal(res.json['accounts'][0]['provider_name'], self.account.provider_name)

    def test_list_googledrive_accounts_returns_accounts_multiple(self):
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account) # self.account is already present
        self.user.save()
        url = api_url_for('list_googledrive_user_accounts', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['accounts'], 2))

    def test_googledrive_config_get_return_correct_urls(self):
        # self.node_settings.set_auth(external_account=self.account, user=self.user)
        url = self.project.api_url_for('googledrive_config_get', Auth(self.user))
        res = self.app.get(url)
        result = res.json['result']
        assert_equal(result['urls']['accounts'],  self.project.api_url_for('list_googledrive_user_accounts'))
        assert_equal(result['urls']['auth'], api_url_for('oauth_connect',
                                                                    service_name='googledrive'))
        assert_equal(result['urls']['config'],  self.project.api_url_for('googledrive_config_put'))
        assert_equal(result['urls']['deauthorize'],  self.project.api_url_for('googledrive_remove_user_auth'))
        assert_equal(result['urls']['files'],  self.project.web_url_for('collect_file_trees'))
        assert_equal(result['urls']['folders'],  self.project.api_url_for('googledrive_folders'))
        assert_equal(result['urls']['importAuth'],  self.project.api_url_for('googledrive_import_user_auth'))
        assert_equal(result['urls']['settings'],  web_url_for('user_addons'))

    def test_googledrive_config_get_has_auth(self):
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.save()
        url = self.project.api_url_for('googledrive_config_get', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_true(result['nodeHasAuth'])

    def test_googledrive_config_get_does_not_has_auth(self):
        url = self.project.api_url_for('googledrive_config_get', Auth(self.user))
        res = self.app.get(url)
        result = res.json['result']
        assert_false(result['nodeHasAuth'])

    def test_googledrive_config_put(self):
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.save()
        url = self.project.api_url_for('googledrive_config_put')
        selected = {
            'path': 'Google Drive/ My Folder',
            'name': 'Google Drive/ My Folder',
            'id': '12345'
        }
        # Can set folder through API call
        res = self.app.put_json(url, {'selected': selected}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        self.node_settings.reload()
        self.project.reload()

        # Folder was set
        assert_equal(self.node_settings.folder_path, 'Google Drive/ My Folder')
        # A log event was created
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'googledrive_folder_selected')
        params = last_log.params
        assert_equal(params['folder_name'], 'Google Drive/ My Folder')

    def test_googledrive_import_user_auth(self):
        url = self.project.api_url_for('googledrive_import_user_auth', auth=self.user.auth)
        self.app.put_json(url, {'external_account_id': self.account._id})
        self.node_settings.reload()
        assert_equal(self.node_settings.external_account, self.account)

    def test_googledrive_remove_user_auth(self):
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.save()
        assert_equal(self.node_settings.external_account, self.account)
        url = self.project.api_url_for('googledrive_remove_user_auth', auth=self.user.auth)
        self.app.delete(url)
        self.node_settings.reload()
        assert_equal(self.node_settings.external_account, None)


class TestGoogleDriveHgridViews(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveHgridViews, self).setUp()
        self.account = GoogleDriveAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        self.user_settings = self.user.get_or_add_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings
        self.user_settings.save()
        self.node_settings.save()
        # Log user in
        self.app.authenticate(*self.user.auth)

    @mock.patch.object(GoogleDriveClient, 'folders')
    def test_googledrive_folders(self, mock_drive_client_folders):
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.save()
        mock_drive_client_folders.return_value = mock_folders['items']
        url = self.project.api_url_for('googledrive_folders', folderId=folderId)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(mock_folders['items']))

    @mock.patch('website.addons.googledrive.views.hgrid.GoogleDriveClient.about')
    def test_googledrive_folders_returns_only_root(self, mock_about):
        mock_about.return_value = {'rootFolderId': '24601'}
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.save()
        url = self.project.api_url_for('googledrive_folders')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(len(res.json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.json[0]['id'], '24601')


class TestGoogleDriveUtils(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveUtils, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        oauth_settings = GoogleDriveOAuthSettingsFactory()
        self.user_settings.oauth_settings = oauth_settings
        self.node_settings.user_settings = self.user_settings
        self.node_settings.folder_id = '09120912'
        self.node_settings.folder_path = 'foo/bar'

        self.user_settings.save()
        self.node_settings.save()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_serialize_settings_helper_returns_correct_urls(self):
        result = serialize_settings(self.node_settings, self.user)
        urls = result['urls']

        assert_equal(urls['files'], self.project.web_url_for('collect_file_trees'))
        assert_equal(urls['config'], self.project.api_url_for('googledrive_config_put'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('googledrive_deauthorize'))
        assert_equal(urls['importAuth'], self.project.api_url_for('googledrive_import_user_auth'))
        # Includes endpoint for fetching folders only
        # NOTE: Querystring params are in camelCase
        assert_equal(urls['get_folders'], self.project.api_url_for('googledrive_folders'))

    def test_serialize_settings_helper_returns_correct_auth_info(self):
        self.user_settings.access_token = 'abc123'
        result = serialize_settings(self.node_settings, self.user)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    def test_serialize_settings_for_user_no_auth(self):
        no_addon_user = AuthUserFactory()
        result = serialize_settings(self.node_settings, no_addon_user)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])

    def test_googledrive_import_user_auth_returns_serialized_settings(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('googledrive_import_user_auth', pid=self.project._primary_key)
        res = self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        expected_result = serialize_settings(self.node_settings, self.user)
        result = res.json['result']
        assert_equal(result, expected_result)
