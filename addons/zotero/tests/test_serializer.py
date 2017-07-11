# -*- coding: utf-8 -*-
"""Serializer tests for the Zotero addon."""
import pytest

from addons.base.tests.serializers import CitationAddonSerializerTestSuiteMixin
from addons.base.tests.utils import MockFolder
from addons.zotero.tests.factories import ZoteroAccountFactory
from addons.zotero.serializer import ZoteroSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestZoteroSerializer(CitationAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'zotero'

    Serializer = ZoteroSerializer
    ExternalAccountFactory = ZoteroAccountFactory
    folder = MockFolder()
