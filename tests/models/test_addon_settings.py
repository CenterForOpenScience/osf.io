from nose.tools import *

from framework.auth.core import Auth
from website.addons import base as addons_base

from tests import base
from tests import factories


class AddonUserSettingsTestCase(base.OsfTestCase):

    OAUTH_PROVIDER = factories.MockOAuth2Provider.short_name

    ADDONS_UNDER_TEST = {
        'mock': {
            'user_settings': factories.MockAddonUserSettings,
            'node_settings': factories.MockAddonNodeSettings,
        },
        'mock_merging': {
            'user_settings': factories.MockAddonUserSettingsMergeable,
            'node_settings': factories.MockAddonNodeSettings,
        },
        OAUTH_PROVIDER: {
            'user_settings': factories.MockOAuthAddonUserSettings,
            'node_settings': factories.MockOAuthAddonNodeSettings,
        },
    }

    def setUp(self):
        super(AddonUserSettingsTestCase, self).setUp()
        self.user = factories.UserFactory()
        self.user.add_addon('mock')
        self.user_settings = self.user.get_addon('mock')
        self.other_user = factories.UserFactory()
        self.project = factories.ProjectFactory(creator=self.other_user)

    def tearDown(self):
        super(AddonUserSettingsTestCase, self).tearDown()
        self.project.reload()
        self.project.remove()
        self.user.remove()

    def test_can_be_merged_not_implemented(self):
        assert_false(self.user_settings.can_be_merged)

    def test_can_be_merged_implemented(self):
        user_settings = self.user.get_or_add_addon('mock_merging')
        assert_true(user_settings.can_be_merged)

    def test_merge_user_settings(self):

        # give the other user an external account
        external_account = factories.ExternalAccountFactory(
            provider=self.OAUTH_PROVIDER
        )
        self.other_user.external_accounts.append(external_account)

        # set up a project, whose addon is authenticated to the other user
        other_user_settings = self.other_user.get_or_add_addon(self.OAUTH_PROVIDER)
        node_settings = self.project.get_or_add_addon(self.OAUTH_PROVIDER, auth=Auth(self.other_user))
        node_settings.set_auth(
            user=self.other_user,
            external_account=external_account
        )

        user_settings = self.user.get_or_add_addon(self.OAUTH_PROVIDER)

        self.user.merge_user(self.other_user)
        self.user.save()

        self.project.reload()
        node_settings.reload()
        user_settings.reload()
        other_user_settings.reload()

        assert_true(node_settings.has_auth)
        assert_in(self.project._id, user_settings.oauth_grants)
        assert_equal(node_settings.user_settings, user_settings)