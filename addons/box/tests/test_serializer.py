# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.box.tests.utils import MockBox
from addons.box.tests.factories import BoxAccountFactory
from tests.base import OsfTestCase
from addons.box.serializer import BoxSerializer

mock_client = MockBox()
pytestmark = pytest.mark.django_db

class TestBoxSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'box'

    Serializer = BoxSerializer
    ExternalAccountFactory = BoxAccountFactory
    client = mock_client

    def setUp(self):
        self.mock_valid = mock.patch.object(
            BoxSerializer,
            'credentials_are_valid',
            return_value=True
        )
        self.mock_valid.start()
        super(TestBoxSerializer, self).setUp()

    def tearDown(self):
        self.mock_valid.stop()
        super(TestBoxSerializer, self).tearDown()

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
