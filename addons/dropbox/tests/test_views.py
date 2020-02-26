"""Views tests for the Dropbox addon."""
from rest_framework import status as http_status
import unittest

from dropbox.exceptions import ApiError
from nose.tools import assert_equal
from tests.base import OsfTestCase
from urllib3.exceptions import MaxRetryError

import mock
import pytest
from addons.base.tests import views as views_testing
from addons.dropbox.tests.utils import (
    DropboxAddonTestCase,
    MockDropbox,
    MockFolderMetadata,
    MockListFolderResult,
    patch_client,
)
from osf_tests.factories import AuthUserFactory

from framework.auth import Auth
from addons.dropbox.serializer import DropboxSerializer
from addons.dropbox.apps import dropbox_root_folder

mock_client = MockDropbox()
pytestmark = pytest.mark.django_db


class TestAuthViews(DropboxAddonTestCase, views_testing.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch(
        'addons.dropbox.models.Provider.auth_url',
        mock.PropertyMock(return_value='http://api.foo.com')
    )
    def test_oauth_start(self):
        super(TestAuthViews, self).test_oauth_start()

    @mock.patch('addons.dropbox.models.UserSettings.revoke_remote_oauth_access', mock.PropertyMock())
    def test_delete_external_account(self):
        super(TestAuthViews, self).test_delete_external_account()


class TestConfigViews(DropboxAddonTestCase, views_testing.OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    folder = {
        'path': '12234',
        'id': '12234'
    }
    Serializer = DropboxSerializer
    client = mock_client

    @mock.patch('addons.dropbox.models.Dropbox', return_value=mock_client)
    def test_folder_list(self, *args):
        super(TestConfigViews, self).test_folder_list()

    @mock.patch.object(DropboxSerializer, 'credentials_are_valid', return_value=True)
    def test_import_auth(self, *args):
        super(TestConfigViews, self).test_import_auth()


class TestFilebrowserViews(DropboxAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('dropbox')
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()

    @mock.patch('addons.dropbox.models.FolderMetadata', new=MockFolderMetadata)
    def test_dropbox_folder_list(self):
        with patch_client('addons.dropbox.models.Dropbox'):
            url = self.project.api_url_for(
                'dropbox_folder_list',
                folder_id='/',
            )
            res = self.app.get(url, auth=self.user.auth)
            contents = [x for x in mock_client.files_list_folder('').entries if isinstance(x, MockFolderMetadata)]
            first = res.json[0]

            assert len(res.json) == len(contents)
            assert 'kind' in first
            assert first['path'] == contents[0].path_display

    @mock.patch('addons.dropbox.models.FolderMetadata', new=MockFolderMetadata)
    @mock.patch('addons.dropbox.models.Dropbox.files_list_folder_continue')
    @mock.patch('addons.dropbox.models.Dropbox.files_list_folder')
    def test_dropbox_folder_list_has_more(self, mock_list_folder, mock_list_folder_continue):
        mock_list_folder.return_value = MockListFolderResult(has_more=True)
        mock_list_folder_continue.return_value = MockListFolderResult()

        url = self.project.api_url_for(
            'dropbox_folder_list',
            folder_id='/',
        )
        res = self.app.get(url, auth=self.user.auth)
        contents = [
            each for each in
            (mock_client.files_list_folder('').entries + mock_client.files_list_folder_continue('').entries)
            if isinstance(each, MockFolderMetadata)
        ]

        mock_list_folder.assert_called_once_with('')
        mock_list_folder_continue.assert_called_once_with('ZtkX9_EHj3x7PMkVuFIhwKYXEpwpLwyxp9vMKomUhllil9q7eWiAu')

        assert len(res.json) == 2
        assert len(res.json) == len(contents)

    def test_dropbox_folder_list_if_folder_is_none_and_folders_only(self):
        with patch_client('addons.dropbox.models.Dropbox'):
            self.node_settings.folder = None
            self.node_settings.save()
            url = self.project.api_url_for('dropbox_folder_list')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.files_list_folder('').entries
            expected = [each for each in contents if isinstance(each, MockFolderMetadata)]
            assert len(res.json) == len(expected)

    def test_dropbox_folder_list_folders_only(self):
        with patch_client('addons.dropbox.models.Dropbox'):
            url = self.project.api_url_for('dropbox_folder_list')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.files_list_folder('').entries
            expected = [each for each in contents if isinstance(each, MockFolderMetadata)]
            assert len(res.json) == len(expected)

    @mock.patch('addons.dropbox.models.Dropbox.files_list_folder')
    def test_dropbox_folder_list_include_root(self, mock_metadata):
        with patch_client('addons.dropbox.models.Dropbox'):
            url = self.project.api_url_for('dropbox_folder_list')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.files_list_folder('').entries
            assert len(res.json) == 1
            assert len(res.json) != len(contents)
            assert res.json[0]['path'] == '/'

    @unittest.skip('finish this')
    def test_dropbox_root_folder(self):
        assert 0, 'finish me'

    def test_dropbox_root_folder_if_folder_is_none(self):
        # Something is returned on normal circumstances
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            root = dropbox_root_folder(node_settings=self.node_settings, auth=self.user.auth)

        assert root is not None

        # Nothing is returned when there is no folder linked
        self.node_settings.folder = None
        self.node_settings.save()
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            root = dropbox_root_folder(node_settings=self.node_settings, auth=self.user.auth)

        assert root is None

    @mock.patch('addons.dropbox.models.Dropbox.files_list_folder')
    def test_dropbox_folder_list_returns_error_if_invalid_path(self, mock_metadata):
        mock_error = mock.Mock()
        mock_metadata.side_effect = ApiError('', mock_error, '', '')
        url = self.project.api_url_for('dropbox_folder_list', folder_id='/fake_path')
        with mock.patch.object(type(self.node_settings), 'has_auth', True):
            res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST


class TestRestrictions(DropboxAddonTestCase, OsfTestCase):

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

    @mock.patch('addons.dropbox.models.Dropbox.files_list_folder')
    def test_restricted_folder_list(self, mock_metadata):
        mock_metadata.return_value = MockListFolderResult()

        # tries to access a parent folder
        url = self.project.api_url_for('dropbox_folder_list',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = self.project.api_url_for('dropbox_set_config')
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has dropbox auth, but is not the node authorizer
        self.contrib.add_addon('dropbox')
        self.contrib.save()

        url = self.project.api_url_for('dropbox_set_config')
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)
