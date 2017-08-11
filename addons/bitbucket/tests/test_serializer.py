# -*- coding: utf-8 -*-
"""Serializer tests for the Bitbucket addon."""

import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from tests.base import OsfTestCase
from addons.bitbucket.api import BitbucketClient
from addons.bitbucket.tests.factories import BitbucketAccountFactory
from addons.bitbucket.serializer import BitbucketSerializer
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin

pytestmark = pytest.mark.django_db

class TestBitbucketSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'bitbucket'

    Serializer = BitbucketSerializer
    ExternalAccountFactory = BitbucketAccountFactory
    client = BitbucketClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid
