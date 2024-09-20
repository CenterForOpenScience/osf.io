"""Serializer tests for the GitLab addon."""
from unittest import mock
import pytest

from tests.base import OsfTestCase
from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.gitlab.api import GitLabClient
from addons.gitlab.tests.factories import GitLabAccountFactory
from addons.gitlab.serializer import GitLabSerializer

pytestmark = pytest.mark.django_db

class TestGitLabSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):

    addon_short_name = 'gitlab'

    Serializer = GitLabSerializer
    ExternalAccountFactory = GitLabAccountFactory
    client = GitLabClient()

    def set_provider_id(self, pid):
        self.node_settings.repo = pid

    ## Overrides ##

    def setUp(self):
        super().setUp()
        self.mock_api_user = mock.patch('addons.gitlab.api.GitLabClient.user')
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super().tearDown()

    def test_serialize_acccount(self):
        ea = self.ExternalAccountFactory()
        expected = {
            'id': ea._id,
            'provider_id': ea.provider_id,
            'provider_name': ea.provider_name,
            'provider_short_name': ea.provider,
            'display_name': ea.display_name,
            'profile_url': ea.profile_url,
            'nodes': [],
            'host': ea.oauth_secret,
            'host_url': ea.oauth_secret,
        }
        assert self.ser.serialize_account(ea) == expected
