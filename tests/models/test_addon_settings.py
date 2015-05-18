from nose.tools import *

from website.addons import base as addons_base

from tests import base
from tests import factories


class AddonUserSettingsTestCase(base.OsfTestCase):

    ADDONS_UNDER_TEST = {
        'mock': {
            'user_settings': factories.MockAddonUserSettings,
            'node_settings': factories.MockAddonNodeSettings,
        },
        'mock_merging': {
            'user_settings': factories.MockAddonUserSettingsMergeable,
            'node_settings': factories.MockAddonNodeSettings,
        }
    }

    def setUp(self):
        super(AddonUserSettingsTestCase, self).setUp()
        self.user = factories.UserFactory()
        self.user.add_addon('mock')
        self.user_settings = self.user.get_addon('mock')

    def tearDown(self):
        super(AddonUserSettingsTestCase, self).tearDown()
        self.user.remove()

    def test_can_be_merged_not_implemented(self):
        assert_false(self.user_settings.can_be_merged)

    def test_can_be_merged_implemented(self):
        user_settings = self.user.get_or_add_addon('mock_merging')
        assert_true(user_settings.can_be_merged)