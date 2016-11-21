# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import assert_equal, ok_

from modularodm import Q

from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase
from website.project.model import Node


PRIVATE, PUBLIC = range(2)


def proj(status=PUBLIC):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    project.update_search()
    return project


def comp(status=PUBLIC):
    project = factories.ProjectFactory(title='Slim Slammity', is_public=status is PUBLIC)
    project.update_search()
    component = factories.NodeFactory(
        title='Flim Flammity',
        parent=project,
        is_public=status is PUBLIC,
    )
    component.update_search()
    return component


class TestNodeFuncs(DbIsolationMixin, OsfTestCase):

    def test_there_are_no_nodes_to_start_with(self):
        assert_equal(Node.find().count(), 0)


    # proj

    def test_proj_makes_private_project_private(self):
        proj(PRIVATE)
        ok_(not Node.find_one().is_public)

    def test_proj_makes_public_project_public(self):
        proj(PUBLIC)
        ok_(Node.find_one().is_public)


    # comp

    def test_comp_makes_private_component_private(self):
        comp(PRIVATE)
        ok_(not Node.find_one(Q('parent_node', 'ne', None)).is_public)

    def test_comp_makes_public_component_public(self):
        comp(PUBLIC)
        ok_(Node.find_one(Q('parent_node', 'ne', None)).is_public)
