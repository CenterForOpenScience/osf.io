# -*- coding: utf-8 -*-
"""Serializer tests for the Bitbucket addon."""

import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from website.addons.bitbucket.api import BitbucketClient
from website.addons.bitbucket.tests.factories import BitbucketAccountFactory
from website.addons.bitbucket.serializer import BitbucketSerializer
from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin


class TestBitbucketSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'bitbucket'

    Serializer = BitbucketSerializer
    ExternalAccountFactory = BitbucketAccountFactory
    client = BitbucketClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid
