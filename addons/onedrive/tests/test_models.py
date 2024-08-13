from unittest import mock
import pytest
import unittest

from framework.auth import Auth
from addons.base.tests.models import OAuthAddonNodeSettingsTestSuiteMixin
from addons.base.tests.models import OAuthAddonUserSettingTestSuiteMixin

from addons.onedrive.models import NodeSettings, OneDriveProvider
from addons.onedrive.client import OneDriveClient
from addons.onedrive.tests.factories import (
    OneDriveAccountFactory,
    OneDriveNodeSettingsFactory,
    OneDriveUserSettingsFactory,
)
from addons.onedrive.tests.utils import raw_root_folder_response, dummy_user_info


pytestmark = pytest.mark.django_db

class TestOneDriveProvider(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.provider = OneDriveProvider()

    @mock.patch.object(OneDriveClient, 'user_info')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = {'id': '12345', 'name': 'fakename', 'link': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert res['provider_id'] == '12345'
        assert res['display_name'] == 'fakename'
        assert res['profile_url'] == 'fakeUrl'


class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'onedrive'
    full_name = 'Microsoft OneDrive'
    ExternalAccountFactory = OneDriveAccountFactory

    def setUp(self):
        super().setUp()

        self.mock_client_folders = mock.patch(
            'addons.onedrive.client.OneDriveClient.folders',
            return_value=raw_root_folder_response,
        )
        self.mock_client_folders.start()

        self.mock_client_user = mock.patch(
            'addons.onedrive.client.OneDriveClient.user_info',
            return_value=dummy_user_info,
        )
        self.mock_client_user.start()

    def tearDown(self):
        self.mock_client_user.stop()
        self.mock_client_folders.stop()

        super().tearDown()


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'onedrive'
    full_name = 'Microsoft OneDrive'
    ExternalAccountFactory = OneDriveAccountFactory

    NodeSettingsFactory = OneDriveNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = OneDriveUserSettingsFactory

    def setUp(self):
        self.mock_refresh = mock.patch.object(
            OneDriveProvider,
            'refresh_oauth_key'
        )
        self.mock_refresh.return_value = True
        self.mock_refresh.start()

        self.mock_client_folders = mock.patch(
            'addons.onedrive.client.OneDriveClient.folders',
            return_value=raw_root_folder_response,
        )
        self.mock_client_folders.start()

        self.mock_client_user = mock.patch(
            'addons.onedrive.client.OneDriveClient.user_info',
            return_value=dummy_user_info,
        )
        self.mock_client_user.start()

        super().setUp()

    def tearDown(self):
        self.mock_client_user.stop()
        self.mock_client_folders.stop()
        self.mock_refresh.stop()
        super().tearDown()

    @mock.patch('addons.onedrive.models.OneDriveProvider')
    def test_api_not_cached(self, mock_odp):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_odp.assert_called_once_with(self.external_account)
        assert api == mock_odp()

    @mock.patch('addons.onedrive.models.OneDriveProvider')
    def test_api_cached(self, mock_odp):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert mock_odp.called is False
        assert api == 'testapi'

    def test_selected_folder_name_root(self):
        self.node_settings.folder_id = 'root'
        assert self.node_settings.selected_folder_name == '/ (Full OneDrive)'

    def test_selected_folder_name_empty(self):
        self.node_settings.folder_id = None
        assert self.node_settings.selected_folder_name == ''

    ## Overrides ##
    def test_set_folder(self):
        folder = {
            'id': 'fake-folder-id',
            'name': 'fake-folder-name',
            'path': 'fake_path'
        }
        self.node_settings.set_folder(folder, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert self.node_settings.folder_id == folder['id']
        # Log was saved
        last_log = self.node.logs.latest()
        assert last_log.action == f'{self.short_name}_folder_selected'

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'folder': self.node_settings.folder_id, 'drive_id': self.node_settings.drive_id}
        assert settings == expected

    def test_set_user_auth_drive_id(self):
        node_settings = self.NodeSettingsFactory()
        user_settings = self.UserSettingsFactory()
        external_account = self.ExternalAccountFactory()

        user_settings.owner.external_accounts.add(external_account)
        user_settings.save()

        node_settings.external_account = external_account
        node_settings.set_auth(external_account, user_settings.owner)
        node_settings.save()

        assert node_settings.drive_id == 'b!aGTf8UN135z3UN35zUN335z3iVNn3mB2ZiWctJ-Dr1N35Uz3q4K'
