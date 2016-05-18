# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
#from onedrive.client import OneDriveClient

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.base.exceptions import AddonError
from website.addons.onedrive.model import OneDriveUserSettings
from website.addons.onedrive.tests.factories import (
    OneDriveNodeSettingsFactory,
    OneDriveUserSettingsFactory
)
#  from website.addons.onedrive.client import (
#      get_client, get_node_addon_client, get_node_client,
#      get_client_from_user_settings
#  )


class TestCore(OsfTestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('onedrive')
        self.user.save()

        self.settings = self.user.get_addon('onedrive')
        self.settings.access_token = '12345'
        self.settings.save()

    def test_get_addon_returns_onedrive_user_settings(self):
        result = self.user.get_addon('onedrive')
        assert_true(isinstance(result, OneDriveUserSettings))


