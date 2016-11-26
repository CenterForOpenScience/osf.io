# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import assert_equal, ok_

from modularodm import Q

from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase
from website.project.model import Node


def _project(is_public):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=is_public)
    project.update_search()
    return project

def public_project(): return _project(True)
def private_project(): return _project(False)


def _component(is_public, parent_is_public):
    project = factories.ProjectFactory(title='Slim Slammity', is_public=parent_is_public)
    project.update_search()
    component = factories.NodeFactory(
        title='Flim Flammity',
        parent=project,
        is_public=is_public,
    )
    component.update_search()
    return component

def public_component_of_public_project(): return _component(True, True)
def public_component_of_private_project(): return _component(True, False)
def private_component_of_public_project(): return _component(False, True)
def private_component_of_private_project(): return _component(False, False)


NODEFUNCS_PRIVATE = [
    private_project,
    private_component_of_public_project,
    private_component_of_private_project
]
NODEFUNCS = [
    public_project,
    public_component_of_public_project,
    public_component_of_private_project
] + NODEFUNCS_PRIVATE


class TestNodeFuncs(DbIsolationMixin, OsfTestCase):

    def test_there_are_no_nodes_to_start_with(self):
        assert_equal(Node.find().count(), 0)


    # pp - {public,private}_project

    def test_pp_makes_public_project_public(self):
        public_project()
        ok_(Node.find_one().is_public)

    def test_pp_makes_private_project_private(self):
        private_project()
        ok_(not Node.find_one().is_public)


    # pcopp - {public,private}_component_of_{public,private}_project

    def test_pcopp_makes_public_component_of_public_project(self):
        public_component_of_public_project()
        component = Node.find_one(Q('parent_node', 'ne', None))
        ok_(component.is_public)
        ok_(component.parent_node.is_public)

    def test_pcopp_makes_public_component_of_private_project(self):
        public_component_of_private_project()
        component = Node.find_one(Q('parent_node', 'ne', None))
        ok_(component.is_public)
        ok_(not component.parent_node.is_public)

    def test_pcopp_makes_private_component_of_public_project(self):
        private_component_of_public_project()
        component = Node.find_one(Q('parent_node', 'ne', None))
        ok_(not component.is_public)
        ok_(component.parent_node.is_public)

    def test_pcopp_makes_private_component_of_private_project(self):
        private_component_of_private_project()
        component = Node.find_one(Q('parent_node', 'ne', None))
        ok_(not component.is_public)
        ok_(not component.parent_node.is_public)
