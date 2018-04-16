# -*- coding: utf-8 -*-
"""Serializer tests for the S3 addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.cloudfiles.tests.factories import CloudFilesAccountFactory
from addons.cloudfiles.serializer import CloudFilesSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestCloudFilesSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'cloudfiles'
    Serializer = CloudFilesSerializer
    ExternalAccountFactory = CloudFilesAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    @mock.patch.object(CloudFilesSerializer, 'credentials_are_valid')
    def test_serialize_settings_authorized_folder_is_set(self, mock_valid):
        mock_valid.return_value = True
        super(TestCloudFilesSerializer, self).test_serialize_settings_authorized_folder_is_set()
