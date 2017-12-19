# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.evernote.model import EvernoteNodeSettings

from website.addons.base.testing import models

from website.addons.evernote.tests.factories import (
    EvernoteUserSettingsFactory,
    EvernoteNodeSettingsFactory,
    EvernoteAccountFactory
)

from website.addons.base.testing import models


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'evernote'
    full_name = 'Evernote'

    NodeSettingsFactory = EvernoteNodeSettingsFactory
    NodeSettingsClass = EvernoteNodeSettings
    UserSettingsFactory = EvernoteUserSettingsFactory
    ExternalAccountFactory = EvernoteAccountFactory

    def test_hello(self):
        assert True


#     def test_folder_defaults_to_none(self):
#         node_settings = BoxNodeSettings(user_settings=self.user_settings)
#         node_settings.save()
#         assert_is_none(node_settings.folder_id)

#     @mock.patch("website.addons.box.model.Box.refresh_oauth_key")
#     def test_serialize_credentials(self, mock_refresh):
#         mock_refresh.return_value = True
#         super(TestNodeSettings, self).test_serialize_credentials()

#     @mock.patch(
#         'website.addons.box.model.BoxUserSettings.revoke_remote_oauth_access',
#         mock.PropertyMock()
#     )
#     def test_complete_has_auth_not_verified(self):
#         super(TestNodeSettings, self).test_complete_has_auth_not_verified()

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'evernote'
    full_name = 'Evernote'
    ExternalAccountFactory = EvernoteAccountFactory

