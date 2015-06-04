
from nose.tools import *
from dateutil.relativedelta import relativedelta

from tests.base import DbTestCase
from tests.factories import ProjectFactory, NodeFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth
from website import models
from scripts.migrate_orphaned_clones import (
    find_orphans, migrate_orphan
)


class TestMigrateOrphanedClones(DbTestCase):

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
        StoredObject._clear_caches()

    def tearDown(self):
        super(TestMigrateOrphanedClones, self).tearDown()
        models.Node.remove()

    def test_find_orphans(self):
        orphans = find_orphans()
        assert_equal(len(orphans), 1)
        assert_equal(orphans[0]._id, self.node_forked._id)

    def test_migrate_orphan_parent_found(self):
        orphans = find_orphans()
        orphan = orphans[0]
        migrate_orphan(orphan, dry_run=False)
        orphan.reload()
        orphan.parent_node.reload()
        self.project_forked.reload()
        assert_equal(orphan.parent_node._id, self.project_forked._id)
        assert_in(orphan._id, self.project_forked.nodes)

    def test_migrate_orphan_no_parent_found_too_early(self):
        self.project_forked.forked_date -= relativedelta(days=1)
        self.project_forked.save()
        orphans = find_orphans()
        orphan = orphans[0]
        migrate_orphan(orphan, dry_run=False)
        orphan.reload()
        assert_false(orphan.parent_node)

    def test_migrate_orphan_no_parent_found_too_late(self):
        self.project_forked.forked_date = relativedelta(days=1)
        self.project_forked.save()
        orphans = find_orphans()
        orphan = orphans[0]
        migrate_orphan(orphan, dry_run=False)
        orphan.reload()
        assert_false(orphan.parent_node)

