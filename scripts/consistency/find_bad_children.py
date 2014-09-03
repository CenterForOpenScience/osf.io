"""Check for consistency errors in parent-child relationships.

"""
from nose.tools import *    #noqa (PEP 8 asserts)

from website import models
from modularodm import Q

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory


def find_orphaned_children(filters=None):
    """Find parents that don't point to their children.

    """
    errors = []
    query = Q('__backrefs.parent.node.nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_parent = models.Node.find(query)
    for child in with_parent:
        if len(child.node__parent) > 1:
            msg = u'Inconsistency: Child {} ({}) has {} parents.'.format(
                child.title,
                child._primary_key,
                len(child.node__parent),
            )
            errors.append(msg)
            continue
        parent = child.node__parent[0]
        if child not in parent.nodes:
            msg = u'Inconsistency: Parent {} ({}) does not point to child {} ({})'.format(
                parent.title,
                parent._primary_key,
                child.title,
                child._primary_key,
            )
            parent.nodes.append(child)
            parent.save()
            errors.append(msg)
    return errors


def find_missing_children(filters=None):
    """Find children that don't point to their parents.

    """
    errors = []
    query = Q('nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_children = models.Node.find(query)
    for parent in with_children:
        for child in parent.nodes:
            if not child.node__parent or child.node__parent[0] != parent:
                msg = u'Inconsistency: Child {} ({}) does not point to parent {} ({})'.format(
                    child.title,
                    child._primary_key,
                    parent.title,
                    parent._primary_key,
                )
                child.node__parent.append(parent)
                child.save()
                errors.append(msg)
    return errors


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

    def test_missing_children(self):
        assert self.parent_project in self.first_child.node__parent

        self.first_child.node__parent = []
        assert self.parent_project not in self.first_child.node__parent

        find_missing_children(filters=None)
        assert self.parent_project in self.first_child.node__parent


if __name__ == '__main__':
    errors = find_missing_children()
    errors = find_orphaned_children()
