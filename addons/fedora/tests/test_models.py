from nose.tools import assert_is_not_none, assert_equal
import pytest
import unittest

from addons.base.tests import models

from addons.fedora.models import NodeSettings
from addons.fedora.tests.factories import (
    FedoraAccountFactory, FedoraNodeSettingsFactory,
    FedoraUserSettingsFactory
)
from addons.fedora.tests import utils
from addons.fedora.settings import USE_SSL

pytestmark = pytest.mark.django_db

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, utils.FedoraAddonTestCase, unittest.TestCase):

    short_name = 'fedora'
    full_name = 'Fedora'
    UserSettingsFactory = FedoraUserSettingsFactory
    ExternalAccountFactory = FedoraAccountFactory


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, utils.FedoraAddonTestCase, unittest.TestCase):

    short_name = 'fedora'
    full_name = 'Fedora'
    ExternalAccountFactory = FedoraAccountFactory
    NodeSettingsFactory = FedoraNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = FedoraUserSettingsFactory

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
