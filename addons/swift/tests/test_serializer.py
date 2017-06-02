# -*- coding: utf-8 -*-
"""Serializer tests for the Swift addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.util import web_url_for
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.swift.tests.factories import SwiftAccountFactory
from addons.swift.serializer import SwiftSerializer

from tests.base import OsfTestCase


class TestSwiftSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'swift'
    Serializer = SwiftSerializer
    ExternalAccountFactory = SwiftAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.swift.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestSwiftSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestSwiftSerializer, self).tearDown()
