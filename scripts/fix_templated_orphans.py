# -*- coding: utf-8 -*-

"""Find orphaned templated nodes without parents, then attempt to identify and
restore their parent nodes. Due to a bug in templating that has since been
fixed, several templated nodes were not attached to the `nodes` lists of their
parents.

"""

import logging

from modularodm import Q

from framework.auth import Auth

from website.models import Node
from website.app import init_app

from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, NodeFactory


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def find_candidate_parents(node):
    return Node.find(
        Q('logs', 'eq', node.logs[0]._id) &
        Q('is_fork', 'eq', node.is_fork) &
        Q('is_registration', 'eq', node.is_registration)
    )


def resolve_templated_orphan(orphan):
    candidate_parents = find_candidate_parents(orphan)
    if candidate_parents.count() != 1:
        logger.warn('Could not identify unique candidate parent for node {}'.format(orphan._id))
        return False
    if candidate_parents[0].date_created != orphan.date_created:
        logger.warn('Creation dates of candidate parent and orphan {} did not match'.format(orphan._id))
    logger.info('Adding orphan to `nodes` list of candidate parent')
    candidate_parents[0].nodes.append(orphan)
    candidate_parents[0].save()
    return True


def find_templated_orphans():
    return Node.find(
        Q('template_node', 'ne', None) &
        Q('category', 'ne', 'project') &
        Q('__backrefs.parent.node.nodes.0', 'exists', False)
    )


if __name__ == '__main__':
    init_app()
    orphans = find_templated_orphans()
    n_resolved = 0
    for orphan in orphans:
        resolved = resolve_templated_orphan(orphan)
        if resolved:
            n_resolved += 1
    logger.info('Done. Resolved {} nodes.'.format(n_resolved))


class TestResolveTemplatedOrphans(OsfTestCase):

    def setUp(self):
        super(TestResolveTemplatedOrphans, self).setUp()
        self.node = NodeFactory()
        self.project = ProjectFactory(creator=self.node.creator)
        self.project.nodes.append(self.node)
        self.project.save()
        self.templated_project = self.project.use_as_template(
            Auth(self.node.creator)
        )
        self.templated_node = self.templated_project.nodes[0]
        self.templated_project.nodes = []
        self.templated_project.save()

    def test_find(self):
        orphans = find_templated_orphans()
        assert_equal(orphans.count(), 1)
        assert_equal(orphans[0], self.templated_node)

    def test_resolve(self):
        assert_not_in(self.templated_node, self.templated_project.nodes)
        resolve_templated_orphan(self.node)
        assert_in(self.node, self.project.nodes)

