# -*- coding: utf-8 -*-
"""Serializer tests for the Bitbucket addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.bitbucket.api import BitbucketClient
from website.addons.bitbucket.tests.factories import BitbucketAccountFactory
from website.addons.bitbucket.serializer import BitbucketSerializer

from tests.base import OsfTestCase

class TestBitbucketSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'bitbucket'

    Serializer = BitbucketSerializer
    ExternalAccountFactory = BitbucketAccountFactory
    client = BitbucketClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid
    
    ## Overrides ##

    def setUp(self):
        super(TestBitbucketSerializer, self).setUp()
        self.mock_api_user = mock.patch("website.addons.bitbucket.api.BitbucketClient.user")
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestBitbucketSerializer, self).tearDown()
