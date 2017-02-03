# -*- coding: utf-8 -*-
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from tests.base import OsfTestCase
from website.addons.base.testing import models

from website.addons.onedrive import model
from website.addons.onedrive.client import OneDriveClient
from website.addons.onedrive.tests.factories import (
    OneDriveAccountFactory,
    OneDriveNodeSettingsFactory,
    OneDriveUserSettingsFactory,
)

class TestOneDriveProvider(OsfTestCase):
    def setUp(self):
        super(TestOneDriveProvider, self).setUp()
        self.provider = model.OneDriveProvider()

    @mock.patch.object(OneDriveClient, 'user_info_for_token')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = {'id': '12345', 'name': 'fakename', 'link': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert_equal(res['provider_id'], '12345')
        assert_equal(res['display_name'], 'fakename')
        assert_equal(res['profile_url'], 'fakeUrl')


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'onedrive'
    full_name = 'Microsoft OneDrive'
    ExternalAccountFactory = OneDriveAccountFactory


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'onedrive'
    full_name = 'Microsoft OneDrive'
    ExternalAccountFactory = OneDriveAccountFactory

    NodeSettingsFactory = OneDriveNodeSettingsFactory
    NodeSettingsClass = model.OneDriveNodeSettings
    UserSettingsFactory = OneDriveUserSettingsFactory

    def setUp(self):
        self.mock_refresh = mock.patch.object(
            model.OneDriveProvider,
            'refresh_oauth_key'
        )
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        super(TestNodeSettings, self).setUp()

    def tearDown(self):
        self.mock_refresh.stop()
        super(TestNodeSettings, self).tearDown()


    @mock.patch('website.addons.onedrive.model.OneDriveProvider')
    def test_api_not_cached(self, mock_odp):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_odp.assert_called_once()
        assert_equal(api, mock_odp())

    @mock.patch('website.addons.onedrive.model.OneDriveProvider')
    def test_api_cached(self, mock_odp):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_odp.called)
        assert_equal(api, 'testapi')

    def test_selected_folder_name_root(self):
        self.node_settings.folder_id = 'root'

        assert_equal(
            self.node_settings.selected_folder_name,
            "/ (Full OneDrive)"
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.folder_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

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
        assert_equal(self.node_settings.folder_id, folder['id'])
        # Log was saved
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'folder': self.node_settings.folder_id}
        assert_equal(settings, expected)
