# -*- coding: utf-8 -*-
"""Serializer tests for the GitHub addon."""
import mock
import pytest

from tests.base import OsfTestCase
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.github.tests.factories import GitHubAccountFactory

from addons.github.api import GitHubClient
from addons.github.serializer import GitHubSerializer

pytestmark = pytest.mark.django_db

class TestGitHubSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'github'

    Serializer = GitHubSerializer
    ExternalAccountFactory = GitHubAccountFactory
    client = GitHubClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid

    ## Overrides ##

    def setUp(self):
        super(TestGitHubSerializer, self).setUp()
        self.mock_api_user = mock.patch('addons.github.api.GitHubClient.user')
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestGitHubSerializer, self).tearDown()
