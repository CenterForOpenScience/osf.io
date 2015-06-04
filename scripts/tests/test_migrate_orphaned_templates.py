from nose.tools import *  # noqa

from tests.base import DbTestCase
from tests.factories import ProjectFactory, NodeFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth
from website import models
from scripts.migrate_orphaned_templates import (
    find_orphans, migrate_orphan
)


class TestMigrateOrphanedTemplates(DbTestCase):

    def setUp(self):
        super(TestMigrateOrphanedTemplates, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node = NodeFactory(creator=self.user, project=self.project)
        self.project_templated = self.project.use_as_template(Auth(user=self.user))
        self.node_templated = self.project_templated.nodes[0]
        self.project_templated.nodes = []
        self.project_templated.save()
        assert_false(self.project_templated.nodes)
        assert_false(self.node_templated.parent_node)
        StoredObject._clear_caches()

    def tearDown(self):
        super(TestMigrateOrphanedTemplates, self).tearDown()
        models.Node.remove()

    def test_find_orphans(self):
        orphans = find_orphans()
        assert_equal(len(orphans), 1)
        assert_equal(orphans[0]._id, self.node_templated._id)

    def test_migrate_orphan_parent_found(self):
        orphans = find_orphans()
        orphan = orphans[0]
        migrate_orphan(orphan, dry_run=False)
        orphan.reload()
        orphan.parent_node.reload()
        self.project_templated.reload()
        assert_equal(orphan.parent_node._id, self.project_templated._id)
        assert_in(orphan._id, self.project_templated.nodes)

    def test_migrate_orphan_parent_not_found(self):
        models.NodeLog.remove_one(self.project_templated.logs[0])
        models.Node.remove_one(self.project_templated)
        orphans = find_orphans()
        orphan = orphans[0]
        migrate_orphan(orphan, dry_run=False)
        orphan.reload()
        assert_false(orphan.parent_node)