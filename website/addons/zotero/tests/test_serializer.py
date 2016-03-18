# -*- coding: utf-8 -*-
"""Serializer tests for the Zotero addon."""

from website.addons.base.testing.serializers import CitationAddonSerializerTestSuiteMixin
from website.addons.base.testing.utils import MockFolder
from website.addons.zotero.tests.factories import ZoteroAccountFactory
from website.addons.zotero.serializer import ZoteroSerializer

from tests.base import OsfTestCase

class TestZoteroSerializer(CitationAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'zotero'

    Serializer = ZoteroSerializer
    ExternalAccountFactory = ZoteroAccountFactory
    folder = MockFolder()
