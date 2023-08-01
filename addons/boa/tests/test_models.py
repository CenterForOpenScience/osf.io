from nose.tools import assert_is_not_none, assert_equal
import pytest
import unittest

from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.boa.models import NodeSettings
from addons.boa.tests.factories import (
    BoaAccountFactory, BoaNodeSettingsFactory,
    BoaUserSettingsFactory
)
from addons.boa.settings import USE_SSL

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'boa'
    full_name = 'boa'
    UserSettingsFactory = BoaUserSettingsFactory
    ExternalAccountFactory = BoaAccountFactory


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'boa'
    full_name = 'boa'
    ExternalAccountFactory = BoaAccountFactory
    NodeSettingsFactory = BoaNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = BoaUserSettingsFactory

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
