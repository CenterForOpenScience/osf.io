import pytest
from scripts.remove_after_use.divorce_quickfiles import create_quickfolders, migrate_quickfiles_to_quickfolders

from osf_tests.factories import AuthUserFactory, NodeLogFactory
from osf.models import OSFUser, QuickFolder, Guid
from osf.utils.testing.pytest_utils import MigrationTestCase
from osf.models.legacy_quickfiles import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile


@pytest.mark.django_db
class TestQuickFilesMigration(MigrationTestCase):

    def test_quickfiles_divorce(self):

        self.bulk_add(10, AuthUserFactory, with_quickfiles_node=True)
        self.sprinkle_quickfiles(11)
        # this is our canary user
        user = OSFUser.objects.last()
        legacy_qf_node = QuickFilesNode.objects.get_for_user(user)
        node_log = NodeLogFactory(user=user)
        legacy_qf_node.logs.add(node_log)

        guid_values = set(QuickFilesNode.objects.all().values_list('guids___id', flat=True))

        # sanity check
        assert OSFUser.objects.all().count() == 10
        create_quickfolders()
        user.refresh_from_db()

        assert QuickFolder.objects.all().count() == 10
        assert isinstance(user.quickfolder, QuickFolder)

        # Everybody targeted with a Quickfolder
        self.assert_joined(QuickFolder, 'target_object_id', OSFUser, 'id')

        # All Quickfolder point somewhere
        assert set(QuickFolder.objects.values_list('guids___id', flat=True)) == guid_values

        migrate_quickfiles_to_quickfolders()
        user.refresh_from_db()

        assert OsfStorageFile.objects.all().count() == 11
        assert Guid.load(legacy_qf_node._id).referent == user.quickfolder

        # We some files will be doubled on a quickfolder up so it's a subset
        self.assert_subset(OsfStorageFile, 'parent_id', QuickFolder, 'id')

        # QuickFilesNode will all be deleted
        assert not QuickFilesNode.objects.all().count()

        # Logs will be transferred unchanged
        log = user.user_logs.first()
        assert node_log.id == log.id
        assert node_log.params == log.params
        assert node_log.action == log.action
