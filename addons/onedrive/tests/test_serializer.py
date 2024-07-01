"""Serializer tests for the OneDrive addon."""
from unittest import mock
import pytest

from addons.onedrive.models import OneDriveProvider
from addons.onedrive.serializer import OneDriveSerializer
from addons.onedrive.tests.factories import OneDriveAccountFactory
from addons.onedrive.tests.utils import MockOneDriveClient, dummy_user_info, raw_root_folder_response
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

mock_client = MockOneDriveClient()

class TestOneDriveSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'onedrive'

    Serializer = OneDriveSerializer
    ExternalAccountFactory = OneDriveAccountFactory
    client = mock_client

    def setUp(self):

        self.mock_client_user = mock.patch(
            'addons.onedrive.client.OneDriveClient.user_info',
            return_value=dummy_user_info,
        )
        self.mock_client_user.start()

        self.mock_client_folders = mock.patch(
            'addons.onedrive.client.OneDriveClient.folders',
            return_value=raw_root_folder_response,
        )
        self.mock_client_folders.start()

        super().setUp()

    def tearDown(self):
        self.mock_client_user.stop()
        self.mock_client_folders.stop()

        super().tearDown()

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
