# -*- coding: utf-8 -*-
"""Views tests for the Box addon."""
import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import httplib
from datetime import datetime

from framework.auth import Auth
from website.util import api_url_for
from urllib3.exceptions import MaxRetryError
from box.client import BoxClientException
from tests.factories import AuthUserFactory

from website.addons.box.model import BoxNodeSettings
from website.addons.box.serializer import BoxSerializer
from website.addons.base import testing
from website.addons.box.tests.utils import (
    BoxAddonTestCase,
    MockBox,
    patch_client
)

mock_client = MockBox()

class TestAuthViews(BoxAddonTestCase, testing.views.OAuthAddonAuthViewsTestCaseMixin):

    def setUp(self):
        self.mock_refresh = mock.patch("website.addons.box.model.Box.refresh_oauth_key")
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        self.mock_update_data = mock.patch.object(
            BoxNodeSettings,
            '_update_folder_data'
        )
        self.mock_update_data.start()
        super(TestAuthViews, self).setUp()

    def tearDown(self):
        self.mock_update_data.stop()
        self.mock_refresh.stop()
        super(TestAuthViews, self).tearDown()

    @mock.patch(
        'website.addons.box.model.BoxUserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestAuthViews, self).test_delete_external_account()


class TestConfigViews(BoxAddonTestCase, testing.views.OAuthAddonConfigViewsTestCaseMixin):

    folder = {
        'path': '/Foo',
        'id': '12234'
    }
    Serializer = BoxSerializer
    client = mock_client

    def setUp(self):
        self.mock_update_data = mock.patch.object(
            BoxNodeSettings,
            '_update_folder_data'
        )
        self.mock_update_data.start()
        super(TestConfigViews, self).setUp()

    def tearDown(self):
        self.mock_update_data.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(BoxSerializer, 'credentials_are_valid', return_value=True)
    def test_import_auth(self, *args):
        super(TestConfigViews, self).test_import_auth()

    @mock.patch.object(BoxNodeSettings, 'fetch_full_folder_path', return_value='/Foo')
    def test_get_config(self, mock_update_folder_data):
        super(TestConfigViews, self).test_get_config()


class TestFilebrowserViews(BoxAddonTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('box')
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()
        self.patcher_fetch = mock.patch('website.addons.box.model.BoxNodeSettings.fetch_folder_name')
        self.patcher_fetch.return_value = 'Camera Uploads'
        self.patcher_fetch.start()
        self.patcher_refresh = mock.patch('website.addons.box.views.Box.refresh_oauth_key')
        self.patcher_refresh.return_value = True
        self.patcher_refresh.start()

    def tearDown(self):
        self.patcher_fetch.stop()
        self.patcher_refresh.stop()

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
