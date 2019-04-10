from osf.utils.testing.pytest_utils import MigrationTestCase
from osf.quickfiles.migration_utils import create_quickfolders, migrate_quickfiles_to_quickfolders

from osf_tests.factories import AuthUserFactory
from osf.models import OSFUser, QuickFolder, Guid
from osf.quickfiles.legacy_quickfiles import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile


class TestQuickFilesMigration(MigrationTestCase):
    number_of_users = 10
    number_of_quickfiles = 10

    def test_0001_quickfiles_divorce(self):
        self.bulk_add(self.number_of_users, AuthUserFactory, with_quickfiles_node=True)
        self.sprinkle_quickfiles(10)

        # this is our canary user
        user = OSFUser.objects.last()
        legacy_qf_node_guid = QuickFilesNode.objects.get_for_user(user)._id

        # sanity check
        assert OSFUser.objects.all().count() == self.number_of_users

        create_quickfolders()
        user.refresh_from_db()

        assert QuickFolder.objects.all().count() == self.number_of_users
        assert isinstance(user.quickfolder, QuickFolder)

        # Everybody targeted with a Quickfolder
        self.assert_joined(QuickFolder, 'target_object_id', OSFUser, 'id')

        migrate_quickfiles_to_quickfolders()
        user.refresh_from_db()

        assert OsfStorageFile.objects.all().count() == self.number_of_quickfiles
        assert Guid.load(legacy_qf_node_guid).referent == user.quickfolder

        # We some files will be doubled on a quickfolder up so it's a subset
        self.assert_subset(OsfStorageFile, 'parent_id', QuickFolder, 'id')
