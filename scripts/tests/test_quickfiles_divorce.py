import pytest
from scripts.divorce_quickfiles import (
    create_quickfolders,
    reverse_create_quickfolders,
    repoint_guids,
    reverse_repoint_guids,
    migrate_quickfiles_to_quickfolders,
    reverse_migrate_quickfiles_to_quickfolders
)

from osf_tests.factories import NodeLogFactory, UserLogFactory
from osf.models import OSFUser, QuickFolder, Guid
from osf.utils.testing.pytest_utils import MigrationTestCase
from osf.models.legacy_quickfiles import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile
from django.contrib.contenttypes.models import ContentType


@pytest.mark.django_db
class TestQuickFilesMigration(MigrationTestCase):

    number_of_quickfiles = 20
    number_of_users = 10

    def test_quickfiles_divorce(self):
        self.add_users(self.number_of_users, with_quickfiles_node=True)
        self.sprinkle_quickfiles(QuickFilesNode, self.number_of_quickfiles)

        # this is our canary user
        user = OSFUser.objects.last()
        legacy_qf_node = QuickFilesNode.objects.get_for_user(user)
        node_log = NodeLogFactory(user=user)
        legacy_qf_node.logs.add(node_log)
        guid_values = set(QuickFilesNode.objects.all().values_list('guids___id', flat=True))

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

        assert not OsfStorageFile.objects.filter(target_content_type=ContentType.objects.get_for_model(QuickFilesNode)).count()
        assert OsfStorageFile.objects.filter(parent_id__type='osf.quickfolder').count() == self.number_of_quickfiles

        # QuickFilesNode will all be deleted
        assert not QuickFilesNode.objects.all().count()

        # Logs will be transferred unchanged
        log = user.user_logs.first()
        assert node_log.id == log.id
        assert node_log.params == log.params
        assert node_log.action == log.action

        # Now that we did everything and test the reverse migration

        # this is our canary user
        user = OSFUser.objects.last()
        user_log = UserLogFactory(user=user)
        user.user_logs.add(user_log)
        guid_values = set(QuickFolder.objects.all().values_list('guids___id', flat=True))

        reverse_create_quickfolders()

        assert self.number_of_users == QuickFilesNode.objects.all().count()
        self.assert_joined(QuickFilesNode, 'creator', OSFUser, 'id')

        reverse_repoint_guids()

        # All Quickfilenodes point somewhere
        assert not QuickFilesNode.objects.filter(guids___id=None)
        # guid_values are a subset because new QuickFilesNode have their guids automatically generated on creation
        assert guid_values.issubset(set(QuickFilesNode.objects.values_list('guids___id', flat=True)))

        reverse_migrate_quickfiles_to_quickfolders()
        user.refresh_from_db()
        # assert Guid.load(user._id).referent == QuickFilesNode.objects.get_for_user(user)

        assert OsfStorageFile.objects.filter(target_content_type=ContentType.objects.get_for_model(QuickFilesNode)).count()\
               == self.number_of_quickfiles
        assert QuickFilesNode.objects.all().count() == self.number_of_users

        # Quickfolders will all be deleted
        assert not QuickFolder.objects.all().count()

        # Logs will be transferred unchanged
        log = user.user_logs.first()
        assert user_log.id == log.id
        assert user_log.params == log.params
        assert user_log.action == log.action

