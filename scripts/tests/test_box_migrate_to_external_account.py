from nose.tools import *

from scripts.box.migrate_to_external_account import do_migration, get_targets

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.addons.box.model import BoxUserSettings
from website.addons.box.tests.factories import BoxOAuthSettingsFactory


class TestBoxMigration(OsfTestCase):
    # Note: BoxUserSettings.user_settings has to be changed to foreign_user_settings (model and mongo). See migration instructions

    def test_migration_no_project(self):

        user = UserFactory()

        user.add_addon('box')
        user_addon = user.get_addon('box')
        user_addon.oauth_settings = BoxOAuthSettingsFactory()
        user_addon.save()

        do_migration([user_addon])
        user_addon.reload()

        assert_is_none(user_addon.oauth_settings)
        assert_equal(len(user.external_accounts), 1)

        account = user.external_accounts[0]
        assert_equal(account.provider, 'box')
        assert_equal(account.oauth_key, 'abcdef1')

    def test_migration_removes_targets(self):
        BoxUserSettings.remove()

        user = UserFactory()
        project = ProjectFactory(creator=user)

        user.add_addon('box', auth=Auth(user))
        user_addon = user.get_addon('box')
        user_addon.oauth_settings = BoxOAuthSettingsFactory()
        user_addon.save()

        project.add_addon('box', auth=Auth(user))
        node_addon = project.get_addon('box')
        node_addon.foreign_user_settings = user_addon
        node_addon.save()

        assert_equal(get_targets().count(), 1)

        do_migration([user_addon])
        user_addon.reload()

        assert_equal(get_targets().count(), 0)

    def test_migration_multiple_users(self):
        user1 = UserFactory()
        user2 = UserFactory()
        oauth_settings = BoxOAuthSettingsFactory()

        user1.add_addon('box')
        user1_addon = user1.get_addon('box')
        user1_addon.oauth_settings = oauth_settings
        user1_addon.save()

        user2.add_addon('box')
        user2_addon = user2.get_addon('box')
        user2_addon.oauth_settings = oauth_settings
        user2_addon.save()

        do_migration([user1_addon, user2_addon])
        user1_addon.reload()
        user2_addon.reload()

        assert_equal(
            user1.external_accounts[0],
            user2.external_accounts[0],
        )

    def test_get_targets(self):
        BoxUserSettings.remove()
        addons = [
            BoxUserSettings(),
            BoxUserSettings(oauth_settings=BoxOAuthSettingsFactory()),
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)
