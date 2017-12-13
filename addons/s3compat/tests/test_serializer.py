# -*- coding: utf-8 -*-
"""Serializer tests for the S3 Compatible Storage addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.s3compat.tests.factories import S3CompatAccountFactory
from addons.s3compat.serializer import S3CompatSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestS3CompatSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 's3compat'
    Serializer = S3CompatSerializer
    ExternalAccountFactory = S3CompatAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.s3compat.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestS3CompatSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestS3CompatSerializer, self).tearDown()
