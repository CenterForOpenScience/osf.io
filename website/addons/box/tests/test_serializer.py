# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.box.tests.utils import MockBox
from website.addons.box.tests.factories import BoxAccountFactory
from website.addons.box.serializer import BoxSerializer

from tests.base import OsfTestCase

mock_client = MockBox()

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
