# -*- coding: utf-8 -*-
import pytest

from framework.auth import Auth
from addons.osfstorage.models import OsfStorageFolder
from osf_tests.factories import (
    ProjectFactory,
    RegionFactory,
    UserFactory,
    CommentFactory,
)
from tests.base import DbTestCase
from osf.management.commands import migrate_deleted_date

class TestMigrateDeletedDate(DbTestCase):

    def setUp(self):
        super(TestMigrateDeletedDate, self).setUp()
        self.region_us = RegionFactory(_id='US', name='United States')

    @pytest.fixture()
    def project(self, user, is_public=True, is_deleted=False, region=None, parent=None):
        if region is None:
            region = self.region_us
        project = ProjectFactory(creator=user, is_public=is_public, is_deleted=is_deleted)
        addon = project.get_addon('osfstorage')
        addon.region = region
        addon.save()

        return project

    @pytest.fixture()
    def user(self):
        return UserFactory()

    def test_populate_with_modified(self):
        statement = migrate_deleted_date.UPDATE_DELETED_WITH_MODIFIED
        table = 'osf_comment'
        user = UserFactory()
        project = ProjectFactory(creator=user)
        comment = CommentFactory(user=user, node=project)

        comment.delete(Auth(user), save=True)
        comment.reload()
        assert(comment.deleted)

        comment.deleted = None
        comment.save()
        migrate_deleted_date.run_statements(statement, 1000, table)
        comment.reload()
        assert(comment.deleted)
        assert(comment.deleted == comment.modified)

    def test_populate_columns(self):
        statement = migrate_deleted_date.POPULATE_BASE_FILE_NODE
        check_statement = migrate_deleted_date.CHECK_BASE_FILE_NODE
        user = UserFactory()
        project = self.project(user)
        osf_folder = OsfStorageFolder.objects.filter(target_object_id=project.id)[0]

        project.remove_node(Auth(user))
        osf_folder.is_root = False
        osf_folder.delete()
        osf_folder.reload()
        project.reload()
        assert(osf_folder.deleted)
        assert(project.deleted)

        project.deleted = None
        osf_folder.deleted = None

        osf_folder.save()
        project.save()
        migrate_deleted_date.run_sql(statement, check_statement, 1000)

        osf_folder.reload()
        assert(osf_folder.deleted)
