# -*- coding: utf-8 -*-
"""Views tests for the Box addon."""
import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import httplib
from datetime import datetime

from framework.auth import Auth
from website.util import api_url_for, web_url_for
from urllib3.exceptions import MaxRetryError
from box.client import BoxClientException
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory

from website.addons.box.tests.utils import (
    BoxAddonTestCase, mock_responses, MockBox, patch_client
)
from website.addons.box.model import BoxOAuthSettings
from website.addons.box.utils import box_addon_folder
from website.addons.box.views.config import serialize_settings

mock_client = MockBox()


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_box_oauth_start(self):
        url = api_url_for('box_oauth_start_user')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.box.views.auth.box_oauth_finish')
    @mock.patch('website.addons.box.views.auth.finish_auth')
    @mock.patch('website.addons.box.views.auth.BoxClient')
    def test_box_oauth_finish(self, mock_get, mock_finish, mock_oauth):
        mock_client = mock.MagicMock()
        mock_client.get_user_info.return_value = {'name': 'Mr. Box', 'id': '1234567890'}
        mock_get.return_value = mock_client
        mock_finish.return_value = {
            'token_type': 'something',
            'access_token': 'something',
            'refresh_token': 'something'
        }
        mock_oauth.return_value = ('mytoken123', 'myboxid', 'done')
        url = api_url_for('box_oauth_finish')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.box.views.auth.flash')
    def test_box_oauth_finish_cancelled(self, mock_flash):
        url = api_url_for('box_oauth_finish', error='User declined!')
        res = self.app.get(url)
        assert_is_redirect(res)
        mock_flash.assert_called_once()

    @mock.patch('website.addons.box.model.BoxOAuthSettings.revoke_access_token')
    def test_box_oauth_delete_user(self, mock_disable_access_token):
        self.user.add_addon('box')
        settings = self.user.get_addon('box')
        oauth = BoxOAuthSettings(user_id='fa;l', access_token='a;lkjadl;kas')
        oauth.save()
        settings.oauth_settings = oauth
        settings.save()
        assert_true(settings.has_auth)
        self.user.save()
        url = api_url_for('box_oauth_delete_user')
        self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)


class TestConfigViews(BoxAddonTestCase):

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.user.add_addon('box')
        settings = self.user.get_addon('box')
        oauth = BoxOAuthSettings(user_id='not none', access_token='Nah')
        oauth.save()
        settings.oauth_settings = oauth
        settings.save()

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    def test_box_user_config_get_has_auth_info(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        url = api_url_for('box_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_true(result['userHasAuth'])

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    def test_box_user_config_get_has_valid_credentials(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        url = api_url_for('box_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_true(result['validCredentials'])

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_user_config_get_has_invalid_credentials(self, mock_get_folder, mock_account_info):
        mock_account_info.side_effect = BoxClientException(401, "The given OAuth 2 access token doesn't exist or has expired.")
        url = api_url_for('box_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_false(result['validCredentials'])

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    def test_box_user_config_get_returns_correct_urls(self, mock_account_info):
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        url = api_url_for('box_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSONified URLs result
        urls = res.json['result']['urls']
        assert_equal(urls['delete'], api_url_for('box_oauth_delete_user'))
        assert_equal(urls['create'], api_url_for('box_oauth_start_user'))

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_helper_returns_correct_urls(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        urls = result['urls']

        assert_equal(urls['config'], self.project.api_url_for('box_config_put'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('box_deauthorize'))
        assert_equal(urls['auth'], self.project.api_url_for('box_oauth_start'))
        assert_equal(urls['importAuth'], self.project.api_url_for('box_import_user_auth'))
        assert_equal(urls['files'], self.project.web_url_for('collect_file_trees'))
        # assert_equal(urls['share'], utils.get_share_folder_uri(self.node_settings.folder))
        # Includes endpoint for fetching folders only
        # NOTE: Querystring params are in camelCase
        assert_equal(urls['folders'], self.project.api_url_for('box_list_folders'))
        assert_equal(urls['settings'], web_url_for('user_addons'))

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_helper_returns_correct_auth_info(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_for_user_no_auth(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        no_addon_user = AuthUserFactory()
        result = serialize_settings(self.node_settings, no_addon_user, client=mock_client)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_valid_credentials(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_true(result['validCredentials'])

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_invalid_credentials(self, mock_get_folder, mock_account_info):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        mock_account_info.side_effect = BoxClientException(401, "The given OAuth 2 access token doesn't exist or has expired.")
        result = serialize_settings(self.node_settings, self.user)
        assert_false(result['validCredentials'])

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_serialize_settings_helper_returns_correct_folder_info(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        folder = result['folder']
        assert_equal(folder['name'], '/' + self.node_settings.folder_name)
        assert_equal(folder['path'], 'All Files/' + self.node_settings.folder_name)

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_config_get(self, mock_get_folder, mock_account_info):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        self.user_settings.save()

        url = api_url_for('box_config_get', pid=self.project._primary_key)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_equal(result['ownerName'], self.user_settings.owner.fullname)

        assert_equal(result['urls']['config'],
            api_url_for('box_config_put', pid=self.project._primary_key))

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_config_put(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        url = api_url_for('box_config_put', pid=self.project._primary_key)
        # Can set folder through API call
        res = self.app.put_json(url, {'selected': {'path': 'My test folder',
            'name': 'Box/My test folder',
            'id': '1234567890'}},
            auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.node_settings.reload()
        self.project.reload()

        # A log event was created
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'box_folder_selected')
        params = last_log.params
        assert_equal(params['folder_id'], '1234567890')
        assert_equal(self.node_settings.folder_id, '1234567890')

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_deauthorize(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        url = api_url_for('box_deauthorize', pid=self.project._primary_key)
        saved_folder = self.node_settings.folder_id
        self.app.delete(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        assert_false(self.node_settings.has_auth)
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        # A log event was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['folder_id'], saved_folder)

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_import_user_auth_returns_serialized_settings(self, mock_get_folder, mock_account_info):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('box_import_user_auth', pid=self.project._primary_key)
        res = self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        expected_result = serialize_settings(self.node_settings, self.user,
                                             client=mock_client)
        result = res.json['result']
        assert_equal(result, expected_result)

    @mock.patch('website.addons.box.client.BoxClient.get_user_info')
    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_import_user_auth_adds_a_log(self, mock_get_folder, mock_account_info):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        mock_account_info.return_value = {'display_name': 'Mr. Box'}
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('box_import_user_auth', pid=self.project._primary_key)
        self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()
        last_log = self.project.logs[-1]

        assert_equal(last_log.action, 'box_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(last_log.user, self.user)

    def test_box_get_share_emails(self):
        # project has some contributors
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('box_get_share_emails', pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        result = res.json['result']
        assert_equal(result['emails'], [u.username for u in self.project.contributors
                                        if u != self.user])

    def test_box_get_share_emails_returns_error_if_not_authorizer(self):
        contrib = AuthUserFactory()
        contrib.add_addon('box')
        contrib.save()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('box_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_box_get_share_emails_requires_user_addon(self):
        # Node doesn't have auth
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('box_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)


class TestFilebrowserViews(BoxAddonTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('box')
        settings = self.user.get_addon('box')
        oauth = BoxOAuthSettings(user_id='not none', access_token='Nah')
        oauth.save()
        settings.oauth_settings = oauth
        settings.save()
        self.patcher = mock.patch('website.addons.box.model.BoxNodeSettings.fetch_folder_name')
        self.patcher.return_value = 'Camera Uploads'
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_box_list_folders(self):
        with patch_client('website.addons.box.views.config.get_node_client'):
            url = self.project.api_url_for('box_list_folders', folderId='foo')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type']=='folder']
            assert_equal(len(res.json), len(expected))
            first = res.json[0]
            assert_in('kind', first)
            assert_equal(first['name'], contents[0]['name'])

    @mock.patch('website.addons.box.model.BoxNodeSettings.folder_id')
    def test_box_list_folders_if_folder_is_none(self, mock_folder):
        # If folder is set to none, no data are returned
        mock_folder.__get__ = mock.Mock(return_value=None)
        url = self.project.api_url_for('box_list_folders')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json), 1)

    def test_box_list_folders_if_folder_is_none_and_folders_only(self):
        with patch_client('website.addons.box.views.config.get_node_client'):
            self.node_settings.folder_name = None
            self.node_settings.save()
            url = api_url_for('box_list_folders',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type']=='folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_folders_only(self):
        with patch_client('website.addons.box.views.config.get_node_client'):
            url = self.project.api_url_for('box_list_folders', foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type']=='folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_doesnt_include_root(self):
        with patch_client('website.addons.box.views.config.get_node_client'):
            url = self.project.api_url_for('box_list_folders', folderId=0)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type'] == 'folder']

            assert_equal(len(res.json), len(expected))

    @unittest.skip('finish this')
    def test_box_addon_folder(self):
        assert 0, 'finish me'

    def test_box_addon_folder_if_folder_is_none(self):
        # Something is returned on normal circumstances
        root = box_addon_folder(
            node_settings=self.node_settings, auth=self.user.auth)
        assert_true(root)

        # The root object is returned w/ None folder
        self.node_settings.folder_name = None
        self.node_settings.save()
        root = box_addon_folder(
            node_settings=self.node_settings, auth=self.user.auth)
        assert_true(root)

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_list_folders_deleted(self, mock_metadata):
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
            u'root': u'box',
            u'size': u'0 bytes',
            u'thumb_exists': False
        }
        url = self.project.api_url_for('box_list_folders', folderId='foo')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_list_folders_returns_error_if_invalid_path(self, mock_metadata):
        mock_metadata.side_effect = BoxClientException(status_code=404, message='File not found')
        url = self.project.api_url_for('box_list_folders', folderId='lolwut')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.box.client.BoxClient.get_folder')
    def test_box_list_folders_handles_max_retry_error(self, mock_metadata):
        mock_response = mock.Mock()
        url = self.project.api_url_for('box_list_folders', folderId='fo')
        mock_metadata.side_effect = MaxRetryError(mock_response, url)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)


class TestRestrictions(BoxAddonTestCase):

    def setUp(self):
        super(BoxAddonTestCase, self).setUp()

        # Nasty contributor who will try to access folders that he shouldn't have
        # access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

        self.user.add_addon('box')
        settings = self.user.get_addon('box')
        settings.access_token = '12345abc'
        settings.last_refreshed = datetime.utcnow()
        settings.save()

        self.patcher = mock.patch('website.addons.box.model.BoxNodeSettings.fetch_folder_name')
        self.patcher.return_value = 'foo bar/baz'
        self.patcher.start()

    @mock.patch('website.addons.box.model.BoxNodeSettings.has_auth')
    def test_restricted_hgrid_data_contents(self, mock_auth):
        mock_auth.__get__ = mock.Mock(return_value=False)

        # tries to access a parent folder
        url = self.project.api_url_for('box_list_folders',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = api_url_for('box_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has box auth, but is not the node authorizer
        self.contrib.add_addon('box')
        self.contrib.save()

        url = api_url_for('box_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)
