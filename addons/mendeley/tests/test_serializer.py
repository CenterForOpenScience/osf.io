# -*- coding: utf-8 -*-
"""Serializer tests for the Mendeley addon."""
import pytest

from addons.base.tests.serializers import CitationAddonSerializerTestSuiteMixin
from addons.base.tests.utils import MockFolder
from addons.mendeley.tests.factories import MendeleyAccountFactory
from addons.mendeley.serializer import MendeleySerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestMendeleySerializer(CitationAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'mendeley'

    Serializer = MendeleySerializer
    ExternalAccountFactory = MendeleyAccountFactory
    folder = MockFolder()
