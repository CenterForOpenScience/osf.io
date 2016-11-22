from nose.tools import *  # noqa

from framework.auth.core import Auth

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory, BookmarkCollectionFactory

from scripts.analytics.addon_snapshot import AddonSnapshot

from website.models import Node
from framework.auth.core import User
from website.settings import ADDONS_AVAILABLE
from website.addons.github.tests.factories import GitHubAccountFactory
from website.addons.github.model import GitHubNodeSettings, GitHubUserSettings
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory
from website.addons.googledrive.model import GoogleDriveNodeSettings, GoogleDriveUserSettings


class TestAddonCount(OsfTestCase):
    def setUp(self):
        super(TestAddonCount, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.user.add_addon('github')
        self.user_addon = self.user.get_addon('github')

        self.external_account = GitHubAccountFactory(display_name='hmoco1')

        self.user_settings = self.user.get_or_add_addon('github')

        self.user_settings.save()
        self.user.external_accounts.append(self.external_account)
        self.user.save()
        self.node.add_addon('github', Auth(self.user))
        self.node_addon = self.node.get_addon('github')
        self.node_addon.user = self.user.fullname
        self.node_addon.repo = '29 #Strafford APTS'
        self.node_addon.user_settings = self.user_addon
        self.node_addon.external_account = self.external_account
        self.node_addon.save()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
    def tearDown(self):
        GitHubNodeSettings.remove()
        GitHubUserSettings.remove()
        GoogleDriveNodeSettings.remove()
        GoogleDriveUserSettings.remove()

    def test_run_for_all_addon(self):
        results = AddonSnapshot().get_events()
        names = [res['provider']['name'] for res in results]
        for addon in ADDONS_AVAILABLE:
            assert_in(addon.short_name, names)

    def test_one_user_one_node_one_addon(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 1)
        assert_equal(github_res['nodes']['total'], 1)

    def test_one_user_one_node_one_addon_one_node_linked(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 1)
        assert_equal(github_res['nodes']['total'], 1)

    def test_one_user_with_multiple_githubs(self):
        oauth_settings2 = GitHubAccountFactory(display_name='hmoco2')
        oauth_settings2.save()
        self.user.external_accounts.append(oauth_settings2)
        self.user.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 1)
        # import ipdb; ipdb.set_trace()

    def test_one_user_with_multiple_addons(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        googledrive_res = [res for res in results if res['provider']['name'] == 'googledrive'][0]
        assert_equal(github_res['users']['enabled'], 1)
        assert_equal(googledrive_res['users']['enabled'], 0)

        self.user.add_addon('googledrive')
        oauth_settings = GoogleDriveAccountFactory()
        oauth_settings.save()
        self.user.external_accounts.append(oauth_settings)
        self.user.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        googledrive_res = [res for res in results if res['provider']['name'] == 'googledrive'][0]
        assert_equal(github_res['users']['enabled'], 1)
        assert_equal(googledrive_res['users']['enabled'], 1)

    def test_many_users_each_with_a_different_github(self):
        user = AuthUserFactory()
        user.add_addon('github')
        oauth_settings2 = GitHubAccountFactory(display_name='hmoco2')
        oauth_settings2.save()
        user.external_accounts.append(oauth_settings2)
        user.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 2)
        assert_equal(github_res['users']['authorized'], 1)
        assert_equal(github_res['users']['linked'], 1)

    def test_many_users_each_with_the_same_github_enabled(self):
        user = AuthUserFactory()
        user.add_addon('github')
        user.external_accounts.append(self.external_account)
        user.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 2)

    def test_github_enabled_not_linked_or_authorized(self):
        user = AuthUserFactory()
        user.add_addon('github')
        user.external_accounts.append(self.external_account)
        user.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['users']['enabled'], 2)
        assert_equal(github_res['users']['authorized'], 1)
        assert_equal(github_res['users']['linked'], 1)

    def test_one_node_with_multiple_addons(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        googledrive_res = [res for res in results if res['provider']['name'] == 'googledrive'][0]
        assert_equal(github_res['nodes']['total'], 1)
        assert_equal(googledrive_res['nodes']['total'], 0)

        self.user.add_addon('googledrive')
        user_addon = self.user.get_addon('googledrive')
        oauth_settings = GoogleDriveAccountFactory()
        oauth_settings.save()
        self.user.external_accounts.append(oauth_settings)
        self.user.save()
        self.node.add_addon('googledrive', Auth(self.user))
        node_addon = self.node.get_addon('googledrive')
        node_addon.user = self.user.fullname
        node_addon.user_settings = user_addon
        node_addon.external_account = oauth_settings
        node_addon.save()
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        googledrive_res = [res for res in results if res['provider']['name'] == 'googledrive'][0]
        assert_equal(github_res['nodes']['total'], 1)
        assert_equal(googledrive_res['nodes']['total'], 1)

    def test_many_nodes_with_one_addon(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['total'], 1)

        node = ProjectFactory(creator=self.user)
        node.add_addon('github', Auth(self.user))
        node_addon = node.get_addon('github')
        node_addon.user = self.user.fullname
        node_addon.repo = '8 (circle)'
        node_addon.user_settings = self.user_addon
        node_addon.external_account = self.external_account
        node_addon.save()
        node.save()

        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['total'], 2)

    def test_node_count_deleted_addon(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['deleted'], 0)

        node = ProjectFactory(creator=self.user)
        node.add_addon('github', Auth(self.user))
        node_addon = node.get_addon('github')
        node_addon.delete()

        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['deleted'], 1)

    def test_node_count_disconected_addon(self):
        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['disconnected'], 0)

        node = ProjectFactory(creator=self.user)
        node.add_addon('github', Auth(self.user))
        node_addon = node.get_addon('github')
        node_addon.external_account = None
        node_addon.save()

        results = AddonSnapshot().get_events()
        github_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(github_res['nodes']['disconnected'], 1)

    def test_all_users_have_wiki_osfstorage_enabled(self):
        all_user_count = User.find().count()
        results = AddonSnapshot().get_events()
        osfstorage_res = [res for res in results if res['provider']['name'] == 'osfstorage'][0]
        wiki_res = [res for res in results if res['provider']['name'] == 'osfstorage'][0]

        assert_equal(osfstorage_res['users']['enabled'], all_user_count)
        assert_equal(wiki_res['users']['enabled'], all_user_count)

    def test_wiki_deleted_shows_as_deleted(self):
        node = ProjectFactory(creator=self.user)
        node.delete_addon('wiki', auth=Auth(self.user))

        results = AddonSnapshot().get_events()
        wiki_res = [res for res in results if res['provider']['name'] == 'wiki'][0]

        assert_equal(wiki_res['nodes']['deleted'], 1)

    def test_node_settings_has_no_owner_not_connected(self):
        self.node_addon.owner = None
        self.node_addon.save()

        results = AddonSnapshot().get_events()
        storage_res = [res for res in results if res['provider']['name'] == 'github'][0]
        assert_equal(storage_res['nodes']['connected'], 0)

    def test_bookmark_collection_not_counted(self):
        BookmarkCollectionFactory(creator=self.user)
        all_node_count = Node.find().count()

        results = AddonSnapshot().get_events()
        storage_res = [res for res in results if res['provider']['name'] == 'osfstorage'][0]
        assert_equal(storage_res['nodes']['connected'], all_node_count - 1)
