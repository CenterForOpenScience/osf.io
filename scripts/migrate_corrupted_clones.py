# -*- coding: utf-8 -*-
"""Backup and remove orphaned registrations and forks with corrupt git repos.
"""

import os
import logging
import subprocess

from website import models
from website import settings
from website.app import init_app

from scripts.migration_utils import (
    backup_collection, backup_node_git, backup_node_mongo,
    UploadsBackupTestCase,
)
from scripts.migrate_orphaned_clones import find_orphans


logger = logging.getLogger(__name__)


def check_node(node):
    """Check whether git repo for node is intact.
    """
    if not node.files_current:
        return True
    try:
        with open(os.devnull, 'w') as fnull:
            subprocess.check_call(
                ['git', 'log'],
                cwd=os.path.join(settings.UPLOADS_PATH, node._id),
                stdout=fnull,
                stderr=fnull,
            )
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return False


def find_corrupt_orphans():
    orphans = find_orphans()
    return [
        each for each in orphans
        if not check_node(each)
    ]


def migrate_orphan(orphan, dry_run=True):
    assert not check_node(orphan)
    logger.warn('Backing up and removing node {0}'.format(orphan._id))
    if not dry_run:
        backup_node_git(orphan)
        backup_node_mongo(orphan)


def main(dry_run=True):
    init_app()
    orphans = find_orphans()
    logger.warn(
        'Found {0} corrupted orphan nodes'.format(
            orphans.count()
        )
    )
    for orphan in orphans:
        migrate_orphan(orphan, dry_run=dry_run)


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    main(dry_run=dry)


from nose.tools import *  # noqa

import copy

from tests.base import DbTestCase
from tests.factories import ProjectFactory, NodeFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth


def get_disk_size(path):
    output = subprocess.check_output(['du', '-sh', path])
    return output.split('\t')[0]


class TestMigrateOrphanedClones(DbTestCase, UploadsBackupTestCase):

    def setUp(self):
        super(TestMigrateOrphanedClones, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node = NodeFactory(creator=self.user, project=self.project)
        self.project_forked = self.project.fork_node(Auth(user=self.user))
        self.node_forked = self.project_forked.nodes[0]
        self.project_forked.nodes = []
        self.project_forked.save()
        assert_false(self.project_forked.nodes)
        assert_false(self.node_forked.parent_node)
        # Must add file for git repo to be provisioned
        self.node_forked.add_file(Auth(user=self.user), 'name', 'content', 7, None)
        assert_true(check_node(self.node_forked))
        # Corrupt the repo
        master_path = os.path.join(
            settings.UPLOADS_PATH,
            self.node_forked._id,
            '.git', 'refs', 'heads', 'master',
        )
        os.remove(master_path)
        assert_false(check_node(self.node_forked))
        StoredObject._clear_caches()

    def tearDown(self):
        super(TestMigrateOrphanedClones, self).tearDown()
        models.Node.remove()
        backup_collection.remove()

    def test_find_orphans(self):
        orphans = find_orphans()
        assert_equal(len(orphans), 1)
        assert_equal(orphans[0]._id, self.node_forked._id)

    def test_migrate_orphan_corrupt(self):
        num_nodes = models.Node.find().count()
        orphans = find_orphans()
        orphan = orphans[0]
        node_data = copy.deepcopy(orphan.to_storage())
        git_path_original = os.path.join(settings.UPLOADS_PATH, orphan._id)
        git_path_backup = os.path.join(settings.UPLOADS_BACKUP_PATH, orphan._id)
        git_size_original = get_disk_size(git_path_original)
        migrate_orphan(orphan, dry_run=False)
        # Orphan is removed from nodes collection
        assert_is(models.Node.load(orphan._id), None)
        # Only one node has been removed
        assert_equal(models.Node.find().count(), num_nodes - 1)
        # Orphan data is present in backup collection
        backup_record = backup_collection.find_one({'_id': orphan._id})
        assert_equal(backup_record, node_data)
        # Only one backup node has been created
        assert_equal(backup_collection.count(), 1)
        # Original git directory has been removed
        assert_false(os.path.exists(git_path_original))
        # Backup git directory has correct size
        git_size_backup = get_disk_size(git_path_backup)
        assert_equal(git_size_original, git_size_backup)

