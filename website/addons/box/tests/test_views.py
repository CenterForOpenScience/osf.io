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
from tests.factories import AuthUserFactory

from website.addons.box.tests.utils import (
    BoxAddonTestCase, mock_responses, MockBox, patch_client
)
from website.addons.box.tests.factories import BoxAccountFactory
from website.addons.box.utils import box_addon_folder
from website.addons.box.serializer import BoxSerializer

mock_client = MockBox()


class TestConfigViews(BoxAddonTestCase):

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.user.add_addon('box')
        self.external_account = self.user.external_accounts[0]
        self.node_settings.external_account = self.external_account
        self.node_settings.save()

    def test_box_get_user_settings_has_account(self):
        url = api_url_for('box_get_user_settings')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        account = res.json.get('accounts')
        assert_is_not_none(account[0])

    def test_box_get_user_settings_not_logged_in(self):
        url = api_url_for('box_get_user_settings')
        self.user = None
        res = self.app.get(url)
        # Redirects to login
        assert_equal(res.status_code, 302)
        assert_in('/login?service=http://localhost:80/api/v1/settings/box/accounts', res.text)

    def test_serialized_urls_returns_correct_urls(self):
        urls = BoxSerializer(node_settings=self.node_settings).serialized_urls

        assert_equal(urls['config'], self.project.api_url_for('box_set_config'))
        assert_equal(urls['auth'], api_url_for('oauth_connect', service_name='box'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('box_remove_user_auth'))
        assert_equal(urls['importAuth'], self.project.api_url_for('box_add_user_auth'))
        assert_equal(urls['files'], self.project.web_url_for('collect_file_trees'))
        # assert_equal(urls['share'], utils.get_share_folder_uri(self.node_settings.folder))
        # Includes endpoint for fetching folders only
        # NOTE: Querystring params are in camelCase
        assert_equal(urls['folders'], self.project.api_url_for('box_folder_list'))
        assert_equal(urls['settings'], web_url_for('user_addons'))

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_serialize_settings_helper_returns_correct_auth_info(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = BoxSerializer().serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
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
        result = BoxSerializer().serialize_settings(self.node_settings, no_addon_user, client=mock_client)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_serialize_settings_valid_credentials(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = BoxSerializer().serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_true(result['validCredentials'])

    @mock.patch('website.addons.box.serializer.BoxClient.get_user_info')
    @mock.patch('website.addons.box.views.BoxClient.get_folder')
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
        result = BoxSerializer().serialize_settings(self.node_settings, self.user)
        assert_false(result['validCredentials'])

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_serialize_settings_helper_returns_correct_folder_info(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        result = BoxSerializer().serialize_settings(self.node_settings, self.user, client=mock_client)
        folder = result['folder']
        assert_equal(folder['name'], '/' + self.node_settings.folder_name)
        assert_equal(folder['path'], 'All Files/' + self.node_settings.folder_name)

    @mock.patch('website.addons.box.serializer.BoxClient.get_user_info')
    @mock.patch('website.addons.box.model.BoxClient.get_folder')
    def test_box_get_config(self, mock_get_folder, mock_account_info):
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

        res = self.app.get(
            self.project.api_url_for('box_get_config'),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_equal(result['ownerName'], self.user_settings.owner.fullname)

        assert_equal(result['urls']['config'],
            api_url_for('box_set_config', pid=self.project._primary_key))

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_box_set_config(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        url = api_url_for('box_set_config', pid=self.project._primary_key)
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

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_box_remove_user_auth(self, mock_get_folder):
        mock_get_folder.return_value = {
            'name': 'Camera Uploads',
            'path_collection': {
                'entries': [
                    {'name': 'All Files'}
                ]
            }
        }
        url = api_url_for('box_remove_user_auth', pid=self.project._primary_key)
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

    @mock.patch('website.addons.box.serializer.BoxClient.get_user_info')
    @mock.patch('website.addons.box.views.BoxClient.get_folder')
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
        url = api_url_for('box_add_user_auth', pid=self.project._primary_key)
        res = self.app.put_json(
            url, 
            {
                'external_account_id': self.external_account._id,
            },
            auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        expected_result = BoxSerializer().serialize_settings(self.node_settings, self.user,
                                             client=mock_client)
        result = res.json['result']
        assert_equal(result, expected_result)

    @mock.patch('website.addons.box.serializer.BoxClient.get_user_info')
    @mock.patch('website.addons.box.views.BoxClient.get_folder')
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
        url = api_url_for('box_add_user_auth', pid=self.project._primary_key)
        self.app.put_json(
            url, 
            {
                'external_account_id': self.external_account._id,
            },
            auth=self.user.auth)
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
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()
        self.patcher = mock.patch('website.addons.box.model.BoxNodeSettings.fetch_folder_name')
        self.patcher.return_value = 'Camera Uploads'
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_box_list_folders(self):
        with patch_client('website.addons.box.views.BoxClient'):
            url = self.project.api_url_for('box_folder_list', folderId='foo')
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
        url = self.project.api_url_for('box_folder_list')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json), 1)

    def test_box_list_folders_if_folder_is_none_and_folders_only(self):
        with patch_client('website.addons.box.views.BoxClient'):
            self.node_settings.folder_name = None
            self.node_settings.save()
            url = api_url_for('box_folder_list',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type']=='folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_folders_only(self):
        with patch_client('website.addons.box.views.BoxClient'):
            url = self.project.api_url_for('box_folder_list', foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type']=='folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_doesnt_include_root(self):
        with patch_client('website.addons.box.views.BoxClient'):
            url = self.project.api_url_for('box_folder_list', folderId=0)
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

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
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
        url = self.project.api_url_for('box_folder_list', folderId='foo')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_box_list_folders_returns_error_if_invalid_path(self, mock_metadata):
        mock_metadata.side_effect = BoxClientException(status_code=404, message='File not found')
        url = self.project.api_url_for('box_folder_list', folderId='lolwut')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)

    @mock.patch('website.addons.box.views.BoxClient.get_folder')
    def test_box_list_folders_handles_max_retry_error(self, mock_metadata):
        mock_response = mock.Mock()
        url = self.project.api_url_for('box_folder_list', folderId='fo')
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
        url = self.project.api_url_for('box_folder_list',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = api_url_for('box_set_config', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has box auth, but is not the node authorizer
        self.contrib.add_addon('box')
        self.contrib.save()

        url = api_url_for('box_set_config', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)
