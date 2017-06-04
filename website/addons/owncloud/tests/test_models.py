from nose.tools import assert_is_not_none, assert_equal

from website.addons.base.testing import models

from website.addons.owncloud.model import AddonOwnCloudNodeSettings
from website.addons.owncloud.tests.factories import (
    OwnCloudAccountFactory, OwnCloudNodeSettingsFactory,
    OwnCloudUserSettingsFactory
)
from website.addons.owncloud.tests import utils
from website.addons.owncloud.settings import USE_SSL

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, utils.OwnCloudAddonTestCase):

    short_name = 'owncloud'
    full_name = 'ownCloud'
    UserSettingsFactory = OwnCloudUserSettingsFactory
    ExternalAccountFactory = OwnCloudAccountFactory


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, utils.OwnCloudAddonTestCase):

    short_name = 'owncloud'
    full_name = 'ownCloud'
    ExternalAccountFactory = OwnCloudAccountFactory
    NodeSettingsFactory = OwnCloudNodeSettingsFactory
    NodeSettingsClass = AddonOwnCloudNodeSettings
    UserSettingsFactory = OwnCloudUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '/Documents',
            'owner': self.node,
            'node': self.node
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
