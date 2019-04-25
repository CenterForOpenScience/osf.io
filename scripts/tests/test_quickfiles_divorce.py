import time

import pytest
from scripts.remove_after_use.divorce_quickfiles import (
    create_quickfolders,
    repoint_guids,
    migrate_quickfiles_to_quickfolders
)

from osf_tests.factories import AuthUserFactory, NodeLogFactory
from osf.models import OSFUser, QuickFolder, Guid
from osf.utils.testing.pytest_utils import MigrationTestCase
from osf.models.legacy_quickfiles import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile


@pytest.mark.django_db
class TestQuickFilesMigration(MigrationTestCase):

    number_of_quickfiles = 20
    number_of_users = 10

    def test_quickfiles_divorce(self):
        self.bulk_add(self.number_of_users, AuthUserFactory, with_quickfiles_node=True)
        self.sprinkle_quickfiles(self.number_of_quickfiles)

        # this is our canary user
        user = OSFUser.objects.last()
        legacy_qf_node = QuickFilesNode.objects.get_for_user(user)
        node_log = NodeLogFactory(user=user)
        legacy_qf_node.logs.add(node_log)
        guid_values = set(QuickFilesNode.objects.all().values_list('guids___id', flat=True))

        # sanity check
        assert OSFUser.objects.all().count() == self.number_of_users
        create_quickfolders()
        user.refresh_from_db()

        assert QuickFolder.objects.all().count() == self.number_of_users
        assert isinstance(user.quickfolder, QuickFolder)

        # Everybody targeted with a Quickfolder
        self.assert_joined(QuickFolder, 'target_object_id', OSFUser, 'id')

        repoint_guids()

        # All Quickfolder point somewhere
        assert not QuickFolder.objects.filter(guids___id=None)
        assert set(QuickFolder.objects.values_list('guids___id', flat=True)) == guid_values

        migrate_quickfiles_to_quickfolders()
        user.refresh_from_db()

        assert Guid.load(legacy_qf_node._id).referent == user.quickfolder

        assert not OsfStorageFile.objects.filter(parent_id__type='osf.quickfilesnode').count()
        assert OsfStorageFile.objects.filter(parent_id__type='osf.quickfolder').count() == self.number_of_quickfiles

        # QuickFilesNode will all be deleted
        assert not QuickFilesNode.objects.all().count()

        # Logs will be transferred unchanged
        log = user.user_logs.first()
        assert node_log.id == log.id
        assert node_log.params == log.params
        assert node_log.action == log.action
