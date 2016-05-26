from nose.tools import *

from scripts.box.migrate_to_external_account import do_migration, get_targets

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.oauth.models import ExternalAccount
from website.addons.box.model import BoxUserSettings, BoxOAuthSettings
from website.addons.box.tests.factories import BoxOAuthSettingsFactory, BoxUserSettingsFactory


class TestBoxMigration(OsfTestCase):
    # Note: BoxUserSettings.user_settings has to be changed to foreign_user_settings (model and mongo). See migration instructions

    def setUp(self):
        super(TestBoxMigration, self).setUp()
        self.user1 = UserFactory()
        self.user1_settings = BoxUserSettingsFactory(owner=self.user1)
        self.user1_settings.oauth_settings = BoxOAuthSettingsFactory()
        self.user1_settings.save()

    def tearDown(self):
        super(TestBoxMigration, self).tearDown()
        BoxUserSettings.remove()
        ExternalAccount.remove()

    def test_migration_no_project(self):
        self.old_oauth = self.user1_settings.oauth_settings
        do_migration([self.user1_settings])
        self.user1_settings.reload()

        assert_is_none(self.user1_settings.oauth_settings)
        assert_equal(len(self.user1.external_accounts), 1)

        account = self.user1_settings.owner.external_accounts[0]
        assert_is_none(self.user1_settings.oauth_settings)
        assert_equal(account.provider, 'box')
        assert_equal(account.oauth_key, self.old_oauth.access_token)

    def test_migration_removes_targets(self):
        project = ProjectFactory(creator=self.user1)

        project.add_addon('box', auth=Auth(self.user1))
        node_addon = project.get_addon('box')
        node_addon.foreign_user_settings = self.user1_settings
        node_addon.save()

        assert_equal(get_targets().count(), 1)

        do_migration([self.user1_settings])
        self.user1_settings.reload()

        assert_equal(get_targets().count(), 0)

    def test_migration_multiple_users(self):
        self.user2 = UserFactory()
        self.user2_settings = BoxUserSettingsFactory(owner=self.user2)
        self.user2_settings.oauth_settings = self.user1_settings.oauth_settings
        self.user2_settings.save()

        do_migration([self.user1_settings, self.user2_settings])
        self.user1_settings.reload()
        self.user2_settings.reload()

        assert_equal(
            self.user1_settings.owner.external_accounts[0],
            self.user2_settings.owner.external_accounts[0],
        )

    def test_get_targets(self):
        self.user2 = UserFactory()
        self.user2_settings = BoxUserSettingsFactory(owner=self.user2)
        self.user2_settings.oauth_settings = None
        self.user2_settings.save()
        addons = [
            self.user2_settings,
            self.user1_settings,
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)
