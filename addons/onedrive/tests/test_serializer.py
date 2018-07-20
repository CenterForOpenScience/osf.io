# -*- coding: utf-8 -*-
"""Serializer tests for the OneDrive addon."""
import pytest

from addons.onedrive.models import OneDriveProvider
from addons.onedrive.serializer import OneDriveSerializer
from addons.onedrive.tests.factories import OneDriveAccountFactory
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestOneDriveSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'onedrive'

    Serializer = OneDriveSerializer
    ExternalAccountFactory = OneDriveAccountFactory
    client = OneDriveProvider

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
