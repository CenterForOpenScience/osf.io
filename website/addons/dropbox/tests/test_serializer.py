# -*- coding: utf-8 -*-
"""Serializer tests for the Dropbox addon."""
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.dropbox.tests.utils import MockDropbox
from website.addons.dropbox.tests.factories import DropboxAccountFactory
from website.addons.dropbox.serializer import DropboxSerializer

from tests.base import OsfTestCase

mock_client = MockDropbox()

class TestDropboxSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'dropbox'

    Serializer = DropboxSerializer
    ExternalAccountFactory = DropboxAccountFactory
    client = mock_client

    def set_provider_id(self, pid):
        self.node_settings.folder = pid
