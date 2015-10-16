from nose.tools import *

from scripts.box.connect_external_accounts import do_migration

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.addons.box.model import BoxUserSettings
from website.addons.box.tests.factories import BoxAccountFactory


class TestBoxPostMergeMigration(OsfTestCase):
    # Note: BoxUserSettings.user_settings has to be changed to foreign_user_settings (model and mongo). See migration instructions

    def test_migration(self):
        BoxUserSettings.remove()

        user = UserFactory()
        node = ProjectFactory(creator=user)
        account = BoxAccountFactory()

        user.external_accounts = [account]

        user.add_addon('box', auth=Auth(user))
        user_addon = user.get_addon('box')
        user_addon.save()


        node.add_addon('box', auth=Auth(user))
        node_addon = node.get_addon('box')
        node_addon.foreign_user_settings = user_addon
        node_addon.folder_id = 'abcdef0'
        node_addon.folder_path = '/'
        node_addon.folder_name = '/ (Full Box)'
        node_addon.save()

        assert_equal(node_addon.external_account, None)
        assert_equal(node_addon.folder_id, 'abcdef0')

        do_migration()
        node_addon.reload()

        assert_equal(node_addon.external_account, account)
        assert_equal(node_addon.folder_id, 'abcdef0')
        assert_equal(node_addon.folder_path, '/')
        assert_equal(node_addon.folder_name, '/ (Full Box)')

    def test_migration_no_account(self):
        BoxUserSettings.remove()

        user = UserFactory()
        node = ProjectFactory(creator=user)

        user.add_addon('box', auth=Auth(user))
        user_addon = user.get_addon('box')
        user_addon.save()

        node.add_addon('box', auth=Auth(user))
        node_addon = node.get_addon('box')
        node_addon.foreign_user_settings = user_addon
        node_addon.save()

        do_migration()  # Would raise exception if fail
