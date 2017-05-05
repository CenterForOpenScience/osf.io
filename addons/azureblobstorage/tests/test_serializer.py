# -*- coding: utf-8 -*-
"""Serializer tests for the AzureBlobStorage addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.util import web_url_for
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.azureblobstorage.tests.factories import AzureBlobStorageAccountFactory
from addons.azureblobstorage.serializer import AzureBlobStorageSerializer

from tests.base import OsfTestCase


class TestAzureBlobStorageSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'azureblobstorage'
    Serializer = AzureBlobStorageSerializer
    ExternalAccountFactory = AzureBlobStorageAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.azureblobstorage.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestAzureBlobStorageSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestAzureBlobStorageSerializer, self).tearDown()
