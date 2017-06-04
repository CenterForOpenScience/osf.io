# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.googledrive.model import GoogleDriveProvider
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory
from website.addons.googledrive.serializer import GoogleDriveSerializer

from tests.base import OsfTestCase

class TestGoogleDriveSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'googledrive'

    Serializer = GoogleDriveSerializer
    ExternalAccountFactory = GoogleDriveAccountFactory
    client = GoogleDriveProvider

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def test_serialized_node_settings_unauthorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=False):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert_in(setting, serialized['result'])

    def test_serialized_node_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert_in(setting, serialized['result'])
        for setting in self.required_settings_authorized:
            assert_in(setting, serialized['result'])