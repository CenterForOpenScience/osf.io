# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
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

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
