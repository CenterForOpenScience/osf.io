# -*- coding: utf-8 -*-
"""Migrate orphaned registrations and forks. Try to indentify a single
candidate parent, matched by the creation log of the node and its cloned date.
"""

import logging

from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.transactions.context import transaction

from website import models
from website.app import init_app


logger = logging.getLogger(__name__)

# Current harakiri setting in uwsgi
OFFSET = relativedelta(seconds=60)


def find_orphans():
    """Find orphaned nodes that are registrations or forks.
    """
    return models.Node.find(
        Q('category', 'ne', 'project') &
        Q('__backrefs.parent.node.nodes.0', 'exists', False) &
        (
            Q('is_registration', 'eq', True) |
            Q('is_fork', 'eq', True)
        )
    )


def find_candidate_parents(node):
    """Find candidate parents for an orphaned node. Candidates must include the
    creation log of the orphan in their `logs` list, must be projects, must not
    be the orphaned node itself, must have the same cloning method as the
    orphan (registered, forked), must be created at approximately the same time
    as the orphan, and must not include any other clones of the orphan in their
    `nodes` lists.
    """
    if not node.logs:
        return []
    if not (node.is_fork or node.is_registration):
        return []
    query = (
        Q('_id', 'ne', node._id) &
        Q('category', 'eq', 'project') &
        Q('logs', 'eq', node.logs[0]._id)
    )
    if node.is_fork:
        query = (
            query &
            Q('is_fork', 'eq', True) &
            Q('forked_date', 'lte', node.forked_date) &
            Q('forked_date', 'gte', node.forked_date - OFFSET)
        )
    if node.is_registration:
        query = (
            query &
            Q('is_registration', 'eq', True) &
            Q('registered_date', 'lte', node.registered_date) &
            Q('registered_date', 'gte', node.registered_date - OFFSET)
        )
    candidates = models.Node.find(query)
    return [
        each for each in candidates
        if not any(node.logs[0] in child.logs for child in each.nodes)
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


from nose.tools import *

from tests.base import DbTestCase
from tests.factories import ProjectFactory, NodeFactory, UserFactory

from framework.mongo import StoredObject
from framework.auth.core import Auth


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
