# -*- coding: utf-8 -*-
"""Views tests for the Box addon."""
from django.utils import timezone
from rest_framework import status as http_status
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import pytest
from urllib3.exceptions import MaxRetryError

from framework.auth import Auth
from website.util import api_url_for
from boxsdk.exception import BoxAPIException
from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory
from addons.base.tests import views as views_testing

from addons.box.models import NodeSettings
from addons.box.serializer import BoxSerializer
from addons.box.tests.utils import (
    BoxAddonTestCase,
    MockBox,
    patch_client,
    mock_responses
)

mock_client = MockBox()
pytestmark = pytest.mark.django_db

class TestAuthViews(BoxAddonTestCase, views_testing.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        self.mock_refresh = mock.patch('addons.box.models.Provider.refresh_oauth_key')
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        super(TestAuthViews, self).setUp()

    def tearDown(self):
        self.mock_refresh.stop()
        super(TestAuthViews, self).tearDown()

    @mock.patch(
        'addons.box.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestAuthViews, self).test_delete_external_account()


class TestConfigViews(BoxAddonTestCase, views_testing.OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    folder = {
        'path': '/Foo',
        'id': '12234'
    }
    Serializer = BoxSerializer
    client = mock_client

    def setUp(self):
        self.mock_data = mock.patch.object(
            NodeSettings,
            '_folder_data',
            return_value=(self.folder['id'], self.folder['path'])
        )
        self.mock_data.start()
        super(TestConfigViews, self).setUp()

    def tearDown(self):
        self.mock_data.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(BoxSerializer, 'credentials_are_valid', return_value=True)
    def test_import_auth(self, *args):
        super(TestConfigViews, self).test_import_auth()

class TestFilebrowserViews(BoxAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('box')
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()
        self.patcher_refresh = mock.patch('addons.box.models.Provider.refresh_oauth_key')
        self.patcher_refresh.return_value = True
        self.patcher_refresh.start()

    def tearDown(self):
        self.patcher_refresh.stop()

    def test_box_list_folders(self):
        with mock.patch('addons.box.models.Client.folder') as folder_mock:
            folder_mock.return_value.get.return_value = mock_responses['folder']
            url = self.project.api_url_for('box_folder_list', folder_id='foo')
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type'] == 'folder']
            assert_equal(len(res.json), len(expected))
            first = res.json[0]
            assert_in('kind', first)
            assert_equal(first['name'], contents[0]['name'])

    @mock.patch('addons.box.models.NodeSettings.folder_id')
    def test_box_list_folders_if_folder_is_none(self, mock_folder):
        # If folder is set to none, no data are returned
        mock_folder.__get__ = mock.Mock(return_value=None)
        url = self.project.api_url_for('box_folder_list')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json), 1)

    def test_box_list_folders_if_folder_is_none_and_folders_only(self):
        with patch_client('addons.box.models.Client'):
            self.node_settings.folder_name = None
            self.node_settings.save()
            url = api_url_for('box_folder_list',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type'] == 'folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_folders_only(self):
        with patch_client('addons.box.models.Client'):
            url = self.project.api_url_for('box_folder_list', foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type'] == 'folder']
            assert_equal(len(res.json), len(expected))

    def test_box_list_folders_doesnt_include_root(self):
        with mock.patch('addons.box.models.Client.folder') as folder_mock:
            folder_mock.return_value.get.return_value = mock_responses['folder']
            url = self.project.api_url_for('box_folder_list', folder_id=0)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.folder('', list=True)['item_collection']['entries']
            expected = [each for each in contents if each['type'] == 'folder']

            assert_equal(len(res.json), len(expected))

    @mock.patch('addons.box.models.Client.folder')
    def test_box_list_folders_returns_error_if_invalid_path(self, mock_metadata):
        mock_metadata.side_effect = BoxAPIException(status=404, message='File not found')
        url = self.project.api_url_for('box_folder_list', folder_id='lolwut')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_404_NOT_FOUND)

    @mock.patch('addons.box.models.Client.folder')
    def test_box_list_folders_handles_max_retry_error(self, mock_metadata):
        mock_response = mock.Mock()
        url = self.project.api_url_for('box_folder_list', folder_id='fo')
        mock_metadata.side_effect = MaxRetryError(mock_response, url)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)


class TestRestrictions(BoxAddonTestCase, OsfTestCase):

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
        settings.last_refreshed = timezone.now()
        settings.save()

        self.patcher = mock.patch('addons.box.models.NodeSettings.fetch_folder_name')
        self.patcher.return_value = 'foo bar/baz'
        self.patcher.start()

    @mock.patch('addons.box.models.NodeSettings.has_auth')
    def test_restricted_hgrid_data_contents(self, mock_auth):
        mock_auth.__get__ = mock.Mock(return_value=False)

        # tries to access a parent folder
        url = self.project.api_url_for('box_folder_list',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = api_url_for('box_set_config', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has box auth, but is not the node authorizer
        self.contrib.add_addon('box')
        self.contrib.save()

        url = api_url_for('box_set_config', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)
