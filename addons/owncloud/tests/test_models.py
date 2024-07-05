import pytest
import unittest

from addons.base.tests.models import OAuthAddonNodeSettingsTestSuiteMixin, OAuthAddonUserSettingTestSuiteMixin
from addons.owncloud.settings import USE_SSL
from addons.owncloud.tests.utils import OwnCloudAddonTestCaseBaseMixin

pytestmark = pytest.mark.django_db


class TestUserSettings(OwnCloudAddonTestCaseBaseMixin, OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    pass


class TestNodeSettings(OwnCloudAddonTestCaseBaseMixin, OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '/Documents',
            'owner': self.node
        }

    def test_serialize_credentials(self):
        credentials = self.node_settings.serialize_waterbutler_credentials()

        assert self.node_settings.external_account.oauth_secret is not None
        expected = {
            'host': self.node_settings.external_account.oauth_secret,
            'password': 'meoword',
            'username': 'catname'
        }

        assert credentials == expected

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder': self.node_settings.folder_id,
            'verify_ssl': USE_SSL
        }
        assert settings == expected
