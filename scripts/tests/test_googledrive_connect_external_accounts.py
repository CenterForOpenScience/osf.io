from nose.tools import *

from scripts.googledrive.connect_external_accounts import do_migration

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.addons.googledrive.model import GoogleDriveUserSettings
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory


class TestGoogleDrivePostMergeMigration(OsfTestCase):
    # Note: GoogleDriveUserSettings.user_settings has to be changed to foreign_user_settings (model and mongo). See migration instructions at https://github.com/CenterForOpenScience/osf.io/pull/4396

    def test_migration(self):
        GoogleDriveUserSettings.remove()

        user = UserFactory()
        node = ProjectFactory(creator=user)
        account = GoogleDriveAccountFactory()

        user.external_accounts = [account]

        user.add_addon('googledrive', auth=Auth(user))
        user_addon = user.get_addon('googledrive')
        user_addon.save()


        node.add_addon('googledrive', auth=Auth(user))
        node_addon = node.get_addon('googledrive')
        node_addon.foreign_user_settings = user_addon
        node_addon.folder_id = 'abcdef0'
        node_addon.folder_path = '/'
        node_addon.save()

        assert_equal(node_addon.external_account, None)
        assert_equal(node_addon.folder_id, 'abcdef0')

        do_migration()
        node_addon.reload()

        assert_equal(node_addon.external_account, account)
        assert_equal(node_addon.folder_id, 'abcdef0')
        assert_equal(node_addon.folder_path, '/')
        assert_equal(node_addon.folder_name, '/ (Full Google Drive)')

    def test_migration_no_account(self):
        GoogleDriveUserSettings.remove()

        user = UserFactory()
        node = ProjectFactory(creator=user)

        user.add_addon('googledrive', auth=Auth(user))
        user_addon = user.get_addon('googledrive')
        user_addon.save()

        node.add_addon('googledrive', auth=Auth(user))
        node_addon = node.get_addon('googledrive')
        node_addon.foreign_user_settings = user_addon
        node_addon.save()

        do_migration()  # Would raise exception if fail
