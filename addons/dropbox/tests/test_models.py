import unittest

import mock
import pytest
from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)
from addons.dropbox.models import NodeSettings
from addons.dropbox.tests import factories

pytestmark = pytest.mark.django_db


class TestDropboxNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):
    full_name = 'dropbox'
    short_name = 'dropbox'

    ExternalAccountFactory = factories.DropboxAccountFactory
    NodeSettingsClass = NodeSettings
    NodeSettingsFactory = factories.DropboxNodeSettingsFactory
    UserSettingsFactory = factories.DropboxUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }

    def test_folder_defaults_to_none(self):
        node_settings = NodeSettings(
            owner=factories.ProjectFactory(),
            user_settings=self.user_settings
        )
        node_settings.save()
        assert node_settings.folder is None

    @mock.patch(
        'addons.dropbox.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super(TestDropboxNodeSettings, self).test_complete_has_auth_not_verified()


class TestDropboxUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    full_name = 'dropbox'
    short_name = 'dropbox'

    ExternalAccountFactory = factories.DropboxAccountFactory
