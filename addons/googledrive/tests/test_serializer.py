# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.googledrive.models import GoogleDriveProvider
from addons.googledrive.tests.factories import GoogleDriveAccountFactory
from addons.googledrive.serializer import GoogleDriveSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

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
