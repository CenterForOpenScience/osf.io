# -*- coding: utf-8 -*-

import logging

from modularodm import Q

from framework.transactions.context import transaction

from website import models
from website.app import init_app


logger = logging.getLogger(__name__)


def find_orphans():
    """Find orphaned nodes created during templating.
    """
    return models.Node.find(
        Q('template_node', 'ne', None) &
        Q('category', 'ne', 'project') &
        Q('__backrefs.parent.node.nodes.0', 'exists', False)
    )


def find_candidate_parents(node):
    """Find candidate parents for an orphaned node. Candidates must include a
    log with the template action created from the parent of the template node of
    the orphaned template. Candidates must also not include any child nodes
    templated from the template node of the orphan.
    """
    template = node.template_node
    if not template:
        return []
    logs = models.NodeLog.find(
        Q('action', 'eq', 'created_from') &
        Q('params.template_node.id', 'eq', node.template_node.parent_node._id)
    )
    return [
        each.node for each in logs
        if not any(child.template_node == template for child in each.node.nodes)
    ]


@transaction()
def migrate_orphan(orphan, dry_run=True):
    parents = find_candidate_parents(orphan)
    if len(parents) == 1:
        parent = parents[0]
        logger.warn(
            'Adding component {0} to `nodes` list of project {1}'.format(
                orphan._id,
                parent._id,
            )
        )
        if not dry_run:
            parent.nodes.append(orphan)
            parent.save()
        return True
    return False


def main(dry_run=True):
    init_app()
    orphans = find_orphans()
    logger.warn(
        'Found {0} orphaned nodes'.format(
            orphans.count()
        )
    )
    count = 0
    for orphan in orphans:
        rescued = migrate_orphan(orphan, dry_run=dry_run)
        if rescued:
            count = 1
    logger.warn('Rescued {0} orphans'.format(count))


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    main(dry_run=dry)


from nose.tools import *  # noqa

from tests.base import DbTestCase
from tests.factories import ProjectFactory, NodeFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth


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

