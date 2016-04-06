# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.box.tests.factories import (
    BoxUserSettingsFactory,
    BoxNodeSettingsFactory,
    BoxAccountFactory
)
from website.addons.box.model import BoxNodeSettings

from website.addons.base.testing import models


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory

    NodeSettingsFactory = BoxNodeSettingsFactory
    NodeSettingsClass = BoxNodeSettings
    UserSettingsFactory = BoxUserSettingsFactory

    def setUp(self):
        self.mock_update_data = mock.patch.object(
            BoxNodeSettings,
            '_update_folder_data'
        )
        self.mock_update_data.start()
        super(TestNodeSettings, self).setUp()

    def tearDown(self):
        self.mock_update_data.stop()
        super(TestNodeSettings, self).tearDown()

    def test_folder_defaults_to_none(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    @mock.patch("website.addons.box.model.Box.refresh_oauth_key")
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        super(TestNodeSettings, self).test_serialize_credentials()

    @mock.patch(
        'website.addons.box.model.BoxUserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super(TestNodeSettings, self).test_complete_has_auth_not_verified()

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory
