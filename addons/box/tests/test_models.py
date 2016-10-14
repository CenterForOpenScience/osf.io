import mock
import unittest

import pytest

from addons.base.tests.models import OAuthAddonNodeSettingsTestSuiteMixin
from addons.base.tests.models import OAuthAddonUserSettingTestSuiteMixin
from addons.box.models import NodeSettings
from addons.box.tests import factories


pytestmark = pytest.mark.django_db


class TestBoxNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):
    full_name = 'Box'
    short_name = 'box'

    ExternalAccountFactory = factories.BoxAccountFactory
    NodeSettingsClass = NodeSettings
    NodeSettingsFactory = factories.BoxNodeSettingsFactory
    UserSettingsFactory = factories.BoxUserSettingsFactory

    def setUp(self):
        self.mock_data = mock.patch.object(
            NodeSettings,
            '_folder_data',
            return_value=('12235', '/Foo')
        )
        self.mock_data.start()
        super(TestBoxNodeSettings, self).setUp()

    def tearDown(self):
        self.mock_data.stop()
        super(TestBoxNodeSettings, self).tearDown()

    def test_folder_defaults_to_none(self):
        node_settings = NodeSettings(user_settings=self.user_settings, owner=factories.ProjectFactory())
        node_settings.save()
        assert node_settings.folder_id is None

    @mock.patch('addons.box.models.Provider.refresh_oauth_key')
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        super(TestBoxNodeSettings, self).test_serialize_credentials()

    @mock.patch('addons.box.models.UserSettings.revoke_remote_oauth_access', mock.PropertyMock())
    def test_complete_has_auth_not_verified(self):
        super(TestBoxNodeSettings, self).test_complete_has_auth_not_verified()


class TestBoxUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    full_name = 'Box'
    short_name = 'box'

    ExternalAccountFactory = factories.BoxAccountFactory
