# -*- coding: utf-8 -*-
"""Serializer tests for the Mendeley addon."""

from website.addons.base.testing.serializers import CitationAddonSerializerTestSuiteMixin
from website.addons.base.testing.utils import MockFolder
from website.addons.mendeley.tests.factories import MendeleyAccountFactory
from website.addons.mendeley.serializer import MendeleySerializer

from tests.base import OsfTestCase

class TestMendeleySerializer(CitationAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'mendeley'

    Serializer = MendeleySerializer
    ExternalAccountFactory = MendeleyAccountFactory
    folder = MockFolder()
