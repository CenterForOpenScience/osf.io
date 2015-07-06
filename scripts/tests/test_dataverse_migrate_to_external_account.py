from nose.tools import *

from scripts.dataverse.migrate_to_external_account import do_migration, get_targets

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.addons.dataverse.model import AddonDataverseUserSettings


class TestDatasetMigration(OsfTestCase):

    def test_migration_no_project(self):

        user = UserFactory()
        api_token = 'api-token-2345'

        user.add_addon('dataverse')
        user_addon = user.get_addon('dataverse')
        user_addon.api_token = api_token
        user_addon.save()

        do_migration([user_addon], dry=False)
        user_addon.reload()

        assert_is_none(user_addon.api_token)
        assert_equal(len(user_addon.external_accounts), 1)

        account = user_addon.external_accounts[0]
        assert_equal(account.provider, 'dataverse')
        assert_equal(account.oauth_key, 'dataverse.harvard.edu')
        assert_equal(account.oauth_secret, api_token)

    def test_migration_includes_project(self):

        user = UserFactory()
        project = ProjectFactory(creator=user)
        api_token = 'api-token-2345'

        user.add_addon('dataverse', auth=Auth(user))
        user_addon = user.get_addon('dataverse')
        user_addon.api_token = api_token
        user_addon.save()

        project.add_addon('dataverse', auth=Auth(user))
        node_addon = project.get_addon('dataverse')
        node_addon.user_settings = user_addon
        node_addon.save()

        do_migration([user_addon], dry=False)
        user_addon.reload()
        node_addon.reload()

        account = user_addon.external_accounts[0]
        assert_equal(account, node_addon.external_account)

    def test_migration_multiple_users(self):
        user1 = UserFactory()
        user2 = UserFactory()
        api_token = 'api-token-2345'

        user1.add_addon('dataverse')
        user1_addon = user1.get_addon('dataverse')
        user1_addon.api_token = api_token
        user1_addon.save()

        user2.add_addon('dataverse')
        user2_addon = user2.get_addon('dataverse')
        user2_addon.api_token = api_token
        user2_addon.save()

        do_migration([user1_addon, user2_addon], dry=False)
        user1_addon.reload()
        user2_addon.reload()

        assert_equal(
            user1_addon.external_accounts[0],
            user2_addon.external_accounts[0],
        )

    def test_get_targets(self):
        AddonDataverseUserSettings.remove()
        addons = [
            AddonDataverseUserSettings(),
            AddonDataverseUserSettings(api_token='api-token-1234'),
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)
