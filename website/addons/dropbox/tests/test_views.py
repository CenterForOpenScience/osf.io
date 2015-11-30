# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""
import httplib as http

import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock

from framework.auth import Auth
from dropbox.rest import ErrorResponse

from urllib3.exceptions import MaxRetryError

from tests.factories import AuthUserFactory

from website.addons.base.testing import views as views_testing
from website.addons.dropbox.tests.utils import (
    DropboxAddonTestCase,
    mock_responses,
    MockDropbox,
    patch_client
)
from website.addons.dropbox.serializer import DropboxSerializer
from website.addons.dropbox.views import dropbox_root_folder

mock_client = MockDropbox()

class TestAuthViews(DropboxAddonTestCase, views_testing.OAuthAddonAuthViewsTestCaseMixin):

    @mock.patch(
        'website.addons.dropbox.model.DropboxProvider.auth_url',
        mock.PropertyMock(return_value='http://api.foo.com')
    )
    def test_oauth_start(self):
        super(TestAuthViews, self).test_oauth_start()

class TestConfigViews(DropboxAddonTestCase, views_testing.OAuthAddonConfigViewsTestCaseMixin):

    folder = {
        'path': '/Foo',
        'id': '12234'
    }
    Serializer = DropboxSerializer
    client = mock_client

    @mock.patch('website.addons.dropbox.views.DropboxClient', return_value=mock_client)
    def test_folder_list(self, *args):
        super(TestConfigViews, self).test_folder_list()


class TestFilebrowserViews(DropboxAddonTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('dropbox')
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()

    def test_dropbox_folder_list(self):
        with patch_client('website.addons.dropbox.views.DropboxClient'):
            url = self.project.api_url_for(
                'dropbox_folder_list',
                folderId='/',
            )
            res = self.app.get(url, auth=self.user.auth)
            contents = [x for x in mock_client.metadata('', list=True)['contents'] if x['is_dir']]
            assert_equal(len(res.json), len(contents))
            first = res.json[0]
            assert_in('kind', first)
            assert_equal(first['path'], contents[0]['path'])

    def test_dropbox_folder_list_if_folder_is_none_and_folders_only(self):
        with patch_client('website.addons.dropbox.views.DropboxClient'):
            self.node_settings.folder = None
            self.node_settings.save()
            url = self.project.api_url_for('dropbox_folder_list')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    def test_dropbox_folder_list_folders_only(self):
        with patch_client('website.addons.dropbox.views.DropboxClient'):
            url = self.project.api_url_for('dropbox_folder_list')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    @mock.patch('website.addons.dropbox.views.DropboxClient.metadata')
    def test_dropbox_folder_list_include_root(self, mock_metadata):
        with patch_client('website.addons.dropbox.views.DropboxClient'):
            url = self.project.api_url_for('dropbox_folder_list')

            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            assert_equal(len(res.json), 1)
            assert_not_equal(len(res.json), len(contents))
            first_elem = res.json[0]
            assert_equal(first_elem['path'], '/')

    @unittest.skip('finish this')
    def test_dropbox_root_folder(self):
        assert 0, 'finish me'

    def test_dropbox_root_folder_if_folder_is_none(self):
        # Something is returned on normal circumstances
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            root = dropbox_root_folder(
                node_settings=self.node_settings, auth=self.user.auth
            )
        assert_true(root)

        # Nothing is returned when there is no folder linked
        self.node_settings.folder = None
        self.node_settings.save()
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            root = dropbox_root_folder(
                node_settings=self.node_settings, auth=self.user.auth
            )
        assert_is_none(root)

    @mock.patch('website.addons.dropbox.views.DropboxClient.metadata')
    def test_dropbox_folder_list_deleted(self, mock_metadata):
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
        url = self.project.api_url_for('dropbox_folder_list', folderId='/tests')
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            res = self.app.get(url, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, http.NOT_FOUND)

    @mock.patch('website.addons.dropbox.views.DropboxClient.metadata')
    def test_dropbox_folder_list_returns_error_if_invalid_path(self, mock_metadata):
        mock_response = mock.Mock()
        mock_metadata.side_effect = ErrorResponse(mock_response, body='File not found')
        url = self.project.api_url_for('dropbox_folder_list', folderId='/fake_path')
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    @mock.patch('website.addons.dropbox.views.DropboxClient.metadata')
    def test_dropbox_folder_list_handles_max_retry_error(self, mock_metadata):
        mock_response = mock.Mock()
        url = self.project.api_url_for('dropbox_folder_list', folderId='/')
        mock_metadata.side_effect = MaxRetryError(mock_response, url)
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.REQUEST_TIMEOUT)


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

    @mock.patch('website.addons.dropbox.views.DropboxClient.metadata')
    def test_restricted_folder_list(self, mock_metadata):
        mock_metadata.return_value = mock_responses['metadata_list']

        # tries to access a parent folder
        url = self.project.api_url_for('dropbox_folder_list',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = self.project.api_url_for('dropbox_set_config')
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has dropbox auth, but is not the node authorizer
        self.contrib.add_addon('dropbox')
        self.contrib.save()

        url = self.project.api_url_for('dropbox_set_config')
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)
