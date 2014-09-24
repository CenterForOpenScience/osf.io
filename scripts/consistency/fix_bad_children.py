"""Find and fix consistency errors in parent-child relationships.

To do a dry run: ::

    python -m scripts.consistency.fix_bad_chidren dry

To run migration: ::

    python -m scripts.consistency.fix_bad_chidren dry

Log:

    Performed on 2014-09-09 by SL. `find_orphaned_children` 2 projects (9 deleted) missing
    forward refs to a child and 8 nodes that had multiple parents.
    with missing forward refs were fixed.
    There was 1 project (deleted) missing a backref to its parent.
    All affected nodes were fixed.

"""
import sys
import logging

from nose.tools import *  # noqa (PEP 8 asserts)

from website import models
from website.app import init_app
from modularodm import Q

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    # Set up MongoStorage backend
    init_app(set_backends=True, routes=False)
    if 'dry' in sys.argv:
        missing_child_errors, _ = find_missing_children(dryrun=True)
        orphaned_child_errors, _ = find_orphaned_children(dryrun=True)
    else:
        missing_child_errors, _ = find_missing_children()
        orphaned_child_errors, _ = find_orphaned_children()
    logger.info('Found {} parents missing forward refs to their children.'.format(len(missing_child_errors)))
    logger.info('Found {} children missing backrefs to their children.'.format(len(orphaned_child_errors)))
    logger.info('Finished.')

def find_orphaned_children(filters=None, dryrun=False):
    """Find parents that don't point to their children.

    """
    errors = []
    fixed = []
    query = Q('__backrefs.parent.node.nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_parent = models.Node.find(query)
    for child in with_parent:
        if len(child.node__parent) > 1:
            children = []
            for parent in child.node__parent:
                children.append('{}: {}'.format(parent, parent.nodes))
            msg = (
                u'Inconsistency: Child {} ({}) has {} parents. The parents are {}. '
                u'The parents have children {}. Manual intervention is necessary.\n'.format(
                    child.title,
                    child._primary_key,
                    len(child.node__parent),
                    child.node__parent,
                    children
                )
            )
            logger.info(msg)
            errors.append(child)
            continue
        parent = child.node__parent[0]
        if child not in parent.nodes:
            msg = u'Inconsistency: Parent {} ({}) does not point to child {} ({}). Attempting to fix.\n'.format(
                parent.title,
                parent._primary_key,
                child.title,
                child._primary_key,
            )
            logger.info(msg)
            errors.append(parent)
            if dryrun is False:
                parent.nodes.append(child)
                parent.save()
                msg = u'Fixed inconsistency: Parent {} ({}) does not point to child {} ({})\n'.format(
                    parent.title,
                    parent._primary_key,
                    child.title,
                    child._primary_key
                )
                logger.info(msg)
                fixed.append(parent)
    return errors, fixed


def find_missing_children(filters=None, dryrun=False):
    """Find children that don't point to their parents.

    """
    errors = []
    fixed = []
    query = Q('nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_children = models.Node.find(query)
    for parent in with_children:
        for child in parent.nodes:
            if not child.node__parent:
                msg = u'Inconsistency: Child {} ({}) does not point to parent {} ({}). Attempting to fix.\n'.format(
                    child.title,
                    child._primary_key,
                    parent.title,
                    parent._primary_key,
                )
                logger.info(msg)
                errors.append(child)
                if dryrun is False:
                    child.node__parent.append(parent)
                    child.save()
                    msg = u'Fixed inconsistency: Child {} ({}) does not point to parent {} ({}).\n'.format(
                        child.title,
                        child._primary_key,
                        parent.title,
                        parent._primary_key
                    )
                    logger.info(msg)
                    fixed.append(child)
    return errors, fixed


class TestParentChildMigration(OsfTestCase):

    def setUp(self):
        super(TestParentChildMigration, self).setUp()
        self.user = UserFactory()
        self.parent_project = ProjectFactory(creator=self.user)
        self.first_child = ProjectFactory(creator=self.user, project=self.parent_project)
        self.second_child = ProjectFactory(creator=self.user, project=self.parent_project)

    def test_orphaned_children(self):
        assert_equal(len(self.parent_project.nodes), 2)
        self.parent_project.nodes.remove(self.second_child)
        assert_equal(len(self.parent_project.nodes), 1)
        find_orphaned_children(filters=None)
        assert_equal(len(self.parent_project.nodes), 2)

    def test_orphaned_children_with_multiple_parents(self):
        first_parent = ProjectFactory(creator=self.user)
        second_parent = ProjectFactory(creator=self.user)
        child = ProjectFactory(creator=self.user)

        first_parent.nodes.append(child)
        first_parent.save()

        second_parent.nodes.append(child)
        second_parent.save()

        errors, fixed = find_orphaned_children(filters=None)
        assert errors[0] == child

    def test_missing_children(self):
        assert self.parent_project in self.first_child.node__parent

        self.first_child.node__parent = []
        assert self.parent_project not in self.first_child.node__parent

        find_missing_children(filters=None)
        assert self.parent_project in self.first_child.node__parent


if __name__ == '__main__':
    main()
