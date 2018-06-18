from nose.tools import assert_is_not_none, assert_equal
import pytest
import unittest

from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.nextcloud.models import NodeSettings
from addons.nextcloud.tests.factories import (
    NextcloudAccountFactory, NextcloudNodeSettingsFactory,
    NextcloudUserSettingsFactory
)
from addons.nextcloud.settings import USE_SSL

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'nextcloud'
    full_name = 'Nextcloud'
    UserSettingsFactory = NextcloudUserSettingsFactory
    ExternalAccountFactory = NextcloudAccountFactory


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'nextcloud'
    full_name = 'Nextcloud'
    ExternalAccountFactory = NextcloudAccountFactory
    NodeSettingsFactory = NextcloudNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = NextcloudUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '/Documents',
            'owner': self.node
        }

    def test_serialize_credentials(self):
        credentials = self.node_settings.serialize_waterbutler_credentials()

        assert_is_not_none(self.node_settings.external_account.oauth_secret)
        expected = {
            'host': self.node_settings.external_account.oauth_secret,
            'password': 'meoword',
            'username': 'catname'
        }

        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder': self.node_settings.folder_id,
            'verify_ssl': USE_SSL
        }
        assert_equal(settings, expected)
