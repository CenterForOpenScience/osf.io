# -*- coding: utf-8 -*-
"""Serializer tests for the OneDriveBusiness addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.onedrivebusiness.tests.factories import OneDriveBusinessAccountFactory
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestOneDriveBusinessSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'onedrivebusiness'
    Serializer = OneDriveBusinessSerializer
    ExternalAccountFactory = OneDriveBusinessAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_get_region_external_account = mock.patch(
            'addons.onedrivebusiness.models.get_region_external_account'
        )
        self.mock_node_settings_oauth_provider_fetch_access_token = mock.patch(
            'addons.onedrivebusiness.models.NodeSettings.oauth_provider.fetch_access_token'
        )
        self.mock_node_settings_ensure_team_folder = mock.patch(
            'addons.onedrivebusiness.models.NodeSettings.ensure_team_folder'
        )
        external_account = mock.Mock()
        external_account.provider_id = 'user-11'
        external_account.oauth_key = 'key-11'
        external_account.oauth_secret = 'secret-15'
        mock_region_external_account = mock.Mock()
        mock_region_external_account.external_account = external_account
        self.mock_get_region_external_account.return_value = mock_region_external_account
        self.mock_node_settings_oauth_provider_fetch_access_token.return_value = 'mock-access-token-1234'

        self.mock_get_region_external_account.start()
        self.mock_node_settings_oauth_provider_fetch_access_token.start()
        self.mock_node_settings_ensure_team_folder.start()
        super(TestOneDriveBusinessSerializer, self).setUp()

    def tearDown(self):
        self.mock_node_settings_ensure_team_folder.stop()
        self.mock_node_settings_oauth_provider_fetch_access_token.stop()
        self.mock_get_region_external_account.stop()
        super(TestOneDriveBusinessSerializer, self).tearDown()
