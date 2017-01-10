# -*- coding: utf-8 -*-
"""Serializer tests for the Figshare addon."""
import mock

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.figshare.tests.factories import FigshareAccountFactory
from website.addons.figshare.serializer import FigshareSerializer

from tests.base import OsfTestCase


class TestFigshareSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'figshare'
    Serializer = FigshareSerializer
    ExternalAccountFactory = FigshareAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    @mock.patch.object(FigshareSerializer, 'credentials_are_valid')
    def test_serialize_settings_authorized_folder_is_set(self, mock_valid):
        mock_valid.return_value = True
        super(TestFigshareSerializer, self).test_serialize_settings_authorized_folder_is_set()
