# -*- coding: utf-8 -*-
"""Serializer tests for the GitHub addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.github.api import GitHubClient
from website.addons.github.tests.factories import GitHubAccountFactory
from website.addons.github.serializer import GitHubSerializer

from tests.base import OsfTestCase

class TestGitHubSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'github'

    Serializer = GitHubSerializer
    ExternalAccountFactory = GitHubAccountFactory
    client = GitHubClient()

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid
    
    ## Overrides ##

    def setUp(self):
        super(TestGitHubSerializer, self).setUp()
        self.mock_api_user = mock.patch("website.addons.github.api.GitHubClient.user")
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestGitHubSerializer, self).tearDown()
