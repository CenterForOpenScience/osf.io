# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""
import os
import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import httplib

from framework.auth import Auth
from website.util import api_url_for, web_url_for
from dropbox.rest import ErrorResponse
from urllib3.exceptions import MaxRetryError
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory

from website.addons.dropbox.tests.utils import (
    DropboxAddonTestCase, mock_responses, MockDropbox, patch_client
)
from website.addons.dropbox.views.config import serialize_settings
from website.addons.dropbox.views.hgrid import dropbox_addon_folder
from website.addons.dropbox import utils

mock_client = MockDropbox()


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_dropbox_oauth_start(self):
        url = api_url_for('dropbox_oauth_start_user')
        res = self.app.get(url)
        assert_is_redirect(res)
        assert_in('&force_reapprove=true', res.location)

    @mock.patch('website.addons.dropbox.views.auth.DropboxOAuth2Flow.finish')
    @mock.patch('website.addons.dropbox.views.auth.get_client_from_user_settings')
    def test_dropbox_oauth_finish(self, mock_get, mock_finish):
        mock_client = mock.MagicMock()
        mock_client.account_info.return_value = {'display_name': 'Mr. Drop Box'}
        mock_get.return_value = mock_client
        mock_finish.return_value = ('mytoken123', 'mydropboxid', 'done')
        url = api_url_for('dropbox_oauth_finish')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.dropbox.client.DropboxClient.disable_access_token')
    def test_dropbox_oauth_delete_user(self, mock_disable_access_token):
        self.user.add_addon('dropbox')
        settings = self.user.get_addon('dropbox')
        settings.access_token = '12345abc'
        settings.save()
        assert_true(settings.has_auth)
        self.user.save()
        url = api_url_for('dropbox_oauth_delete_user')
        self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)

    @mock.patch('website.addons.dropbox.client.DropboxClient.disable_access_token')
    def test_dropbox_oauth_delete_user_with_invalid_credentials(self, mock_disable_access_token):
        self.user.add_addon('dropbox')
        settings = self.user.get_addon('dropbox')
        settings.access_token = '12345abc'
        settings.save()
        assert_true(settings.has_auth)

        mock_response = mock.Mock()
        mock_response.status = 401
        mock_disable_access_token.side_effect = ErrorResponse(mock_response, "The given OAuth 2 access token doesn't exist or has expired.")

        self.user.save()
        url = api_url_for('dropbox_oauth_delete_user')
        self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)


class TestConfigViews(DropboxAddonTestCase):

    def test_dropbox_user_config_get_has_auth_info(self):
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_true(result['userHasAuth'])

    @mock.patch('website.addons.dropbox.client.DropboxClient.account_info')
    def test_dropbox_user_config_get_has_valid_credentials(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Drop Box'}
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_true(result['validCredentials'])

    @mock.patch('website.addons.dropbox.client.DropboxClient.account_info')
    def test_dropbox_user_config_get_has_invalid_credentials(self, mock_account_info):
        mock_response = mock.Mock()
        mock_response.status = 401
        mock_account_info.side_effect = ErrorResponse(mock_response, "The given OAuth 2 access token doesn't exist or has expired.")
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_false(result['validCredentials'])

    def test_dropbox_user_config_get_returns_correct_urls(self):
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSONified URLs result
        urls = res.json['result']['urls']
        assert_equal(urls['delete'], api_url_for('dropbox_oauth_delete_user'))
        assert_equal(urls['create'], api_url_for('dropbox_oauth_start_user'))

    def test_serialize_settings_helper_returns_correct_urls(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        urls = result['urls']

        assert_equal(urls['config'], self.project.api_url_for('dropbox_config_put'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('dropbox_deauthorize'))
        assert_equal(urls['auth'], self.project.api_url_for('dropbox_oauth_start'))
        assert_equal(urls['importAuth'], self.project.api_url_for('dropbox_import_user_auth'))
        assert_equal(urls['files'], self.project.web_url_for('collect_file_trees'))
        assert_equal(urls['share'], utils.get_share_folder_uri(self.node_settings.folder))
        # Includes endpoint for fetching folders only
        # NOTE: Querystring params are in camelCase
        assert_equal(urls['folders'],
            self.project.api_url_for('dropbox_hgrid_data_contents', root=1))
        assert_equal(urls['settings'], web_url_for('user_addons'))

    def test_serialize_settings_helper_returns_correct_auth_info(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    def test_serialize_settings_for_user_no_auth(self):
        no_addon_user = AuthUserFactory()
        result = serialize_settings(self.node_settings, no_addon_user, client=mock_client)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])

    @mock.patch('website.addons.dropbox.client.DropboxClient.account_info')
    def test_serialize_settings_valid_credentials(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Drop Box'}
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_true(result['validCredentials'])

    @mock.patch('website.addons.dropbox.client.DropboxClient.account_info')
    def test_serialize_settings_invalid_credentials(self, mock_account_info):
        mock_response = mock.Mock()
        mock_response.status = 401
        mock_account_info.side_effect = ErrorResponse(mock_response, "The given OAuth 2 access token doesn't exist or has expired.")
        result = serialize_settings(self.node_settings, self.user)
        assert_false(result['validCredentials'])

    def test_serialize_settings_helper_returns_correct_folder_info(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        folder = result['folder']
        assert_equal(folder['name'], self.node_settings.folder)
        assert_equal(folder['path'], self.node_settings.folder)

    def test_dropbox_config_get(self):
        self.user_settings.save()

        url = api_url_for('dropbox_config_get', pid=self.project._primary_key)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_equal(result['ownerName'], self.user_settings.owner.fullname)

        assert_equal(result['urls']['config'],
            api_url_for('dropbox_config_put', pid=self.project._primary_key))

    def test_dropbox_config_put(self):
        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
        # Can set folder through API call
        res = self.app.put_json(url, {'selected': {'path': 'My test folder',
            'name': 'Dropbox/My test folder'}},
            auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.node_settings.reload()
        self.project.reload()

        # Folder was set
        assert_equal(self.node_settings.folder, 'My test folder')
        # A log event was created
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_folder_selected')
        params = last_log.params
        assert_equal(params['folder'], 'My test folder')

    def test_dropbox_deauthorize(self):
        url = api_url_for('dropbox_deauthorize', pid=self.project._primary_key)
        saved_folder = self.node_settings.folder
        self.app.delete(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        assert_false(self.node_settings.has_auth)
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder, None)

        # A log event was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['folder'], saved_folder)

    @mock.patch('website.addons.dropbox.client.DropboxClient.account_info')
    def test_dropbox_import_user_auth_returns_serialized_settings(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Drop Box'}
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_import_user_auth', pid=self.project._primary_key)
        res = self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        expected_result = serialize_settings(self.node_settings, self.user,
                                             client=mock_client)
        result = res.json['result']
        assert_equal(result, expected_result)

    def test_dropbox_import_user_auth_adds_a_log(self):
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_import_user_auth', pid=self.project._primary_key)
        self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()
        last_log = self.project.logs[-1]

        assert_equal(last_log.action, 'dropbox_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(last_log.user, self.user)

    def test_dropbox_get_share_emails(self):
        # project has some contributors
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        result = res.json['result']
        assert_equal(result['emails'], [u.username for u in self.project.contributors
                                        if u != self.user])
        assert_equal(result['url'], utils.get_share_folder_uri(self.node_settings.folder))

    def test_dropbox_get_share_emails_returns_error_if_not_authorizer(self):
        contrib = AuthUserFactory()
        contrib.add_addon('dropbox')
        contrib.save()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_dropbox_get_share_emails_requires_user_addon(self):
        # Node doesn't have auth
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)


class TestFilebrowserViews(DropboxAddonTestCase):

    def test_dropbox_hgrid_data_contents(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for(
                'dropbox_hgrid_data_contents',
                path=self.node_settings.folder,
                pid=self.project._primary_key,
            )
            res = self.app.get(url, auth=self.user.auth)
            contents = [x for x in mock_client.metadata('', list=True)['contents'] if x['is_dir']]
            assert_equal(len(res.json), len(contents))
            first = res.json[0]
            assert_in('kind', first)
            assert_equal(first['path'], contents[0]['path'])

    def test_dropbox_hgrid_data_contents_if_folder_is_none_and_folders_only(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            self.node_settings.folder = None
            self.node_settings.save()
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    def test_dropbox_hgrid_data_contents_folders_only(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_include_root(self, mock_metadata):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, root=1)

            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            assert_equal(len(res.json), 1)
            assert_not_equal(len(res.json), len(contents))
            first_elem = res.json[0]
            assert_equal(first_elem['path'], '/')

    @unittest.skip('finish this')
    def test_dropbox_addon_folder(self):
        assert 0, 'finish me'

    def test_dropbox_addon_folder_if_folder_is_none(self):
        # Something is returned on normal circumstances
        root = dropbox_addon_folder(
            node_settings=self.node_settings, auth=self.user.auth)
        assert_true(root)

        # Nothing is returned when there is no folder linked
        self.node_settings.folder = None
        self.node_settings.save()
        root = dropbox_addon_folder(
            node_settings=self.node_settings, auth=self.user.auth)
        assert_is_none(root)

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_deleted(self, mock_metadata):
        # Example metadata for a deleted folder
        mock_metadata.return_value = {
            u'bytes': 0,
            u'contents': [],
            u'hash': u'e3c62eb85bc50dfa1107b4ca8047812b',
            u'icon': u'folder_gray',
            u'is_deleted': True,
            u'is_dir': True,
            u'modified': u'Sat, 29 Mar 2014 20:11:49 +0000',
            u'path': u'/tests',
            u'rev': u'3fed844002c12fc',
            u'revision': 67033156,
            u'root': u'dropbox',
            u'size': u'0 bytes',
            u'thumb_exists': False
        }
        url = self.project.api_url_for('dropbox_hgrid_data_contents')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_returns_error_if_invalid_path(self, mock_metadata):
        mock_response = mock.Mock()
        mock_metadata.side_effect = ErrorResponse(mock_response, body='File not found')
        url = self.project.api_url_for('dropbox_hgrid_data_contents')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_handles_max_retry_error(self, mock_metadata):
        mock_response = mock.Mock()
        url = self.project.api_url_for('dropbox_hgrid_data_contents')
        mock_metadata.side_effect = MaxRetryError(mock_response, url)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.REQUEST_TIMEOUT)


class TestRestrictions(DropboxAddonTestCase):

    def setUp(self):
        super(DropboxAddonTestCase, self).setUp()

        # Nasty contributor who will try to access folders that he shouldn't have
        # access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

        # Set shared folder
        self.node_settings.folder = 'foo bar/bar'
        self.node_settings.save()

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_restricted_hgrid_data_contents(self, mock_metadata):
        mock_metadata.return_value = mock_responses['metadata_list']

        # tries to access a parent folder
        url = self.project.api_url_for('dropbox_hgrid_data_contents',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has dropbox auth, but is not the node authorizer
        self.contrib.add_addon('dropbox')
        self.contrib.save()

        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)
