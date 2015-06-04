import os

from nose.tools import *  # noqa

import copy

from tests.base import DbTestCase, UploadsBackupTestCase
from tests.factories import ProjectFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth

from website import models, settings
from scripts.migrate_corrupted_clones import get_disk_size
from scripts.migrate_node_without_logs import (
    find_nodes_without_logs, migrate_node
)
from scripts.utils import backup_collection


class TestMigrateNodesWithoutLogs(DbTestCase, UploadsBackupTestCase):

    def setUp(self):
        super(TestMigrateNodesWithoutLogs, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project_without_logs = ProjectFactory(creator=self.user)
        self.project_without_logs.add_file(Auth(user=self.user), 'name', 'content', 7, None)
        assert_true(self.project_without_logs.logs)
        self.project_without_logs.logs = []
        self.project_without_logs.save()
        assert_false(self.project_without_logs.logs)
        StoredObject._clear_caches()

    def tearDown(self):
        super(TestMigrateNodesWithoutLogs, self).tearDown()
        models.Node.remove()
        backup_collection.remove()

    def test_find_nodes_without_logs(self):
        nodes = find_nodes_without_logs()
        assert_equal(len(nodes), 1)
        assert_equal(nodes[0]._id, self.project_without_logs._id)

    def test_backup_nodes_without_logs(self):
        nodes = find_nodes_without_logs()
        node = nodes[0]
        git_path_original = os.path.join(settings.UPLOADS_PATH, node._id)
        git_path_backup = os.path.join(settings.UPLOADS_BACKUP_PATH, node._id)
        git_size_original = get_disk_size(git_path_original)
        num_nodes = models.Node.find().count()
        node_data = copy.deepcopy(node.to_storage())
        migrate_node(node, dry_run=False)
        assert_equal(models.Node.find().count(), num_nodes - 1)
        assert_equal(backup_collection.count(), 1)
        assert_equal(backup_collection.find_one(), node_data)
        # Original git directory has been removed
        assert_false(os.path.exists(git_path_original))
        # Backup git directory has correct size
        git_size_backup = get_disk_size(git_path_backup)
        assert_equal(git_size_original, git_size_backup)
