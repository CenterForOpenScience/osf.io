from nose.tools import *

from website.addons import base as addons_base

from tests import base
from tests import factories


class MockUserSettings(addons_base.AddonUserSettingsBase):
    pass


class MockNodeSettings(addons_base.AddonNodeSettingsBase):
    pass


class MockMergeUserSettings(addons_base.AddonUserSettingsBase):
    def merge(self, user_settings):
        pass


class MockMergeNodeSetting(addons_base.AddonNodeSettingsBase):
    pass


class AddonUserSettingsTestCase(base.OsfTestCase):

    ADDONS_UNDER_TEST = {
        'mock': {
            'user_settings': MockUserSettings,
            'node_settings': MockNodeSettings,
        },
        'mock_merging': {
            'user_settings': MockMergeUserSettings,
            'node_settings': MockMergeNodeSetting,
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