# -*- coding: utf-8 -*-
"""Serializer tests for the GitLab addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.gitlab.api import GitLabClient
from website.addons.gitlab.tests.factories import GitLabAccountFactory
from website.addons.gitlab.serializer import GitLabSerializer

from tests.base import OsfTestCase

class TestGitLabSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'gitlab'

    Serializer = GitLabSerializer
    ExternalAccountFactory = GitLabAccountFactory
    client = GitLabClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid
    
    ## Overrides ##

    def setUp(self):
        super(TestGitLabSerializer, self).setUp()
        self.mock_api_user = mock.patch("website.addons.gitlab.api.GitLabClient.user")
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestGitLabSerializer, self).tearDown()
