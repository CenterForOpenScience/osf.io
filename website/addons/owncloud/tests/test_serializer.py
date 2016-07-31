# -*- coding: utf-8 -*-
"""Serializer tests for the OwnCloud addon."""
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.owncloud.tests.utils import MockOwnCloud
from website.addons.owncloud.tests.factories import OwnCloudAccountFactory
from website.addons.owncloud.serializer import OwnCloudSerializer

from tests.base import OsfTestCase

mock_client = MockOwnCloud()

class TestOwnCloudSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'owncloud'

    Serializer = OwnCloudSerializer
    ExternalAccountFactory = OwnCloudAccountFactory
    client = mock_client

    def set_provider_id(self, pid):
        self.node_settings.folder = pid
