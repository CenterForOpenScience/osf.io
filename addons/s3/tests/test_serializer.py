# -*- coding: utf-8 -*-
"""Serializer tests for the S3 addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.s3.tests.factories import S3AccountFactory
from addons.s3.serializer import S3Serializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestS3Serializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 's3'
    Serializer = S3Serializer
    ExternalAccountFactory = S3AccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.s3.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestS3Serializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestS3Serializer, self).tearDown()
