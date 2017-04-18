from nose.tools import assert_is_not_none, assert_equal

from website.addons.base.testing import models

from website.addons.fedora.model import AddonFedoraNodeSettings
from website.addons.fedora.tests.factories import (
    FedoraAccountFactory, FedoraNodeSettingsFactory,
    FedoraUserSettingsFactory
)
from website.addons.fedora.tests import utils
from website.addons.fedora.settings import USE_SSL

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, utils.FedoraAddonTestCase):

    short_name = 'fedora'
    full_name = 'ownCloud'
    UserSettingsFactory = FedoraUserSettingsFactory
    ExternalAccountFactory = FedoraAccountFactory


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, utils.FedoraAddonTestCase):

    short_name = 'fedora'
    full_name = 'ownCloud'
    ExternalAccountFactory = FedoraAccountFactory
    NodeSettingsFactory = FedoraNodeSettingsFactory
    NodeSettingsClass = AddonFedoraNodeSettings
    UserSettingsFactory = FedoraUserSettingsFactory

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
            'repo': self.node_settings.external_account.oauth_secret,
            'password': 'meoword',
            'user': 'catname'
        }

        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder': self.node_settings.folder_id,
            'verify_ssl': USE_SSL
        }
        assert_equal(settings, expected)
