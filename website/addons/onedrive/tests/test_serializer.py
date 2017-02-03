# -*- coding: utf-8 -*-
"""Serializer tests for the OneDrive addon."""

import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from website.addons.onedrive.model import OneDriveProvider
from website.addons.onedrive.serializer import OneDriveSerializer
from website.addons.onedrive.tests.factories import OneDriveAccountFactory
from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin


class TestOneDriveSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'onedrive'

    Serializer = OneDriveSerializer
    ExternalAccountFactory = OneDriveAccountFactory
    client = OneDriveProvider

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
