# -*- coding: utf-8 -*-
import mock
import time
import datetime

from nose.tools import *  # noqa
from framework.auth import Auth
from website.util import api_url_for
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory, ProjectFactory

from website.addons.googledrive.tests.utils import mock_folders
from website.addons.googledrive.utils import serialize_settings
from website.addons.googledrive.tests.utils import mock_root_folders


class TestGoogleDriveAuthViews(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveAuthViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings
        # Log user in
        self.app.authenticate(*self.user.auth)
        self.flow = mock.Mock()
        self.credentials = mock.Mock()

    # Class variables(self) are usually used to mark mock variables. Can be removed later.
    @mock.patch('website.addons.googledrive.views.auth.OAuth2WebServerFlow')
    def test_googledrive_oauth_start(self, mock_flow):
        url = api_url_for('googledrive_oauth_start_user', Auth(self.user))
        mock_flow.return_value = self.flow
        mock_params = {}
        self.flow.params = mock_params
        mock_params['approval_prompt'] = 'force'
        self.flow.step1_get_authorize_url.return_value = 'fake.url'
        res = self.app.post(url)
        assert_true(res.json['url'], 'fake.url')

    @mock.patch('website.addons.googledrive.views.auth.build')
    @mock.patch('website.addons.googledrive.views.auth.OAuth2WebServerFlow')
    @mock.patch('website.addons.googledrive.views.auth.session')
    def test_googledrive_oauth_finish(self, mock_session, mock_flow, mock_build):
        user_no_addon = AuthUserFactory()
        nid = self.project._primary_key
        fake_token_expiry = datetime.datetime.now()
        mock_session.data.get.return_value = nid
        mock_access_token = mock.Mock()
        mock_flow.return_value = self.flow
        self.flow.step2_exchange.return_value = self.credentials
        self.credentials.authorize.return_value = mock_access_token
        self.credentials.access_token = '1111'
        self.credentials.refresh_token = '2222'
        self.credentials.token_expiry = fake_token_expiry
        self.service = mock.Mock()
        mock_build.return_value = self.service
        self.mock_get = mock.Mock()
        self.service.about.return_value = self.mock_get
        self.mock_execute = mock.Mock()
        self.mock_get.get.return_value = self.mock_execute
        username = {'name': 'fakename', 'user': {'emailAddress': 'fakeemailid.com'}}
        self.mock_execute.execute.return_value = username
        url = api_url_for('googledrive_oauth_finish', user_no_addon.auth, nid=self.project._primary_key, code='1234')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.googledrive.views.auth.build')
    @mock.patch('website.addons.googledrive.views.auth.OAuth2WebServerFlow')
    def test_googledrive_oauth_finish_user_only(self, mock_flow, mock_build):
        user_no_addon = AuthUserFactory()
        mock_access_token = mock.Mock()
        fake_token_expiry = datetime.datetime.now()
        mock_flow.return_value = self.flow
        self.flow.step2_exchange.return_value = self.credentials
        self.credentials.authorize.return_value = mock_access_token
        self.credentials.access_token = '1111'
        self.credentials.refresh_token = '2222'
        self.credentials.token_expiry = fake_token_expiry
        self.service = mock.Mock()
        mock_build.return_value = self.service
        self.mock_get = mock.Mock()
        self.service.about.return_value = self.mock_get
        self.mock_execute = mock.Mock()
        self.mock_get.get.return_value = self.mock_execute
        username = {'name':'fakename', 'user': {'emailAddress': 'fakeemailid.com'}}
        self.mock_execute.execute.return_value = username
        url = api_url_for('googledrive_oauth_finish', user_no_addon.auth, code='1234')
        res = self.app.get(url)
        assert_is_redirect(res)

    def test_googledrive_oauth_delete_user(self):
        self.user_settings.access_token = 'abc123'
        self.user_settings.save()
        assert_true(self.user_settings.has_auth)
        self.user.save()
        url = api_url_for('googledrive_oauth_delete_user')
        self.app.delete(url)
        self.user_settings.reload()
        assert_false(self.user_settings.has_auth)

    def test_googledrive_deauthorize(self):
        self.node_settings.folder_id = 'foobar'
        self.node_settings.folder_path = 'My folder'
        self.node_settings.save()

        url = self.project.api_url_for('googledrive_deauthorize')

        self.app.delete(url)
        self.project.reload()
        self.node_settings.reload()

        assert_false(self.node_settings.has_auth)
        assert_is(self.node_settings.folder_id, None)
        assert_is(self.node_settings.folder_path, None)
        assert_is(self.node_settings.user_settings, None)


class TestGoogleDriveConfigViews(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveConfigViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_drive_user_config_get_returns_correct_urls(self):
        self.user.add_addon('googledrive')
        url = api_url_for('googledrive_user_config_get', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        result = res.json['result']['urls']
        assert_true(result['create'], api_url_for('googledrive_oauth_start_user'))
        assert_true(result['delete'], api_url_for('googledrive_oauth_delete_user'))

    def test_drive_user_config_get_has_auth(self):
        self.user.add_addon('googledrive')
        user_settings = self.user.get_addon('googledrive')
        user_settings.access_token = 'abc123'
        user_settings.save()
        url = api_url_for('googledrive_user_config_get', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_true(result['userHasAuth'])

    def test_drive_user_config_get_not_has_auth(self):
        url = api_url_for('googledrive_user_config_get', Auth(self.user))
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_false(result['userHasAuth'])

    # TODO
    def test_googledrive_config_put(self):
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
        assert_equal(params['folder'], 'Google Drive/ My Folder')


class TestGoogleDriveHgridViews(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveHgridViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings
        self.user_settings.save()
        self.node_settings.save()
        # Log user in
        self.app.authenticate(*self.user.auth)

    @mock.patch('website.addons.googledrive.views.hgrid.AccessTokenCredentials')
    @mock.patch('website.addons.googledrive.views.hgrid.build')
    def test_googledrive_folders(self, mock_build, mock_access_token_credentials):
        folderId = '12345'
        self.credentials = mock.Mock()
        mock_access_token_credentials.return_value = self.credentials
        self.http_service = mock.Mock()
        self.credentials.authorize.return_value = self.http_service
        self.service = mock.Mock()
        mock_build.return_value = self.service
        self.mock_list = mock.Mock()
        self.mock_files = mock.Mock()
        folders = mock_folders
        self.service.files.return_value = self.mock_files
        self.mock_files.list.return_value = self.mock_list
        self.mock_list.execute.return_value = folders
        url = api_url_for('googledrive_folders', pid=self.project._primary_key, folderId=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        expected = [items for items in mock_folders['items']]
        assert_equal(len(res.json), len(expected))

    @mock.patch('website.addons.googledrive.views.hgrid.AccessTokenCredentials')
    @mock.patch('website.addons.googledrive.views.hgrid.build')
    def test_googledrive_folders_returns_only_root_folders(self, mock_build, mock_access_token_credentials):
        folderId = ''
        self.credentials = mock.Mock()
        mock_access_token_credentials.return_value = self.credentials
        self.http_service = mock.Mock()
        self.credentials.authorize.return_value = self.http_service
        self.service = mock.Mock()
        mock_build.return_value = self.service
        self.mock_list = mock.Mock()
        self.mock_files = mock.Mock()
        folders = mock_root_folders
        self.service.files.return_value = self.mock_files
        self.mock_files.list.return_value = self.mock_list
        self.mock_list.execute.return_value = folders
        url = api_url_for('googledrive_folders', pid=self.project._primary_key, folderId=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        expected = [items for items in mock_root_folders['items']]
        assert_equal(len(res.json), len(expected))


class TestGoogleDriveUtils(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveUtils, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('googledrive')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', Auth(self.user))
        self.node_settings = self.project.get_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        self.node_settings.user_settings = self.user_settings

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
        assert_equal(
            urls['get_folders'],
            self.project.api_url_for('googledrive_folders', includeRoot=1),
        )

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
