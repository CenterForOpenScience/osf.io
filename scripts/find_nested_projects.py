#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper to get a list of all projects that are nested within another project."""

from website.project.model import Node
from modularodm import Q

from tests.base import OsfTestCase
from tests.factories import ProjectFactory


def find_nested_projects():
    return Node.find(
            Q('__backrefs.parent.node.nodes.0', 'exists', True) &
            Q('category', 'eq', 'project') &
            Q('is_deleted', 'eq', False)
    )
    #return [node for node in Node.find()
            #if node.category == 'project'
            #and node.parent_node is not None]

class TestFindNestedProjects(OsfTestCase):

    def test_find_nested(self):
        project =ProjectFactory.build()
        nested_project = ProjectFactory()
        project.nodes.append(nested_project)
        project.save()

        result = find_nested_projects()
        assert nested_project in result
        assert project not in result

    def test_unnested_project(self):
        project = ProjectFactory()
        assert project not in find_nested_projects()

    def test_deleted_projects_excluded(self):
        project = ProjectFactory.build()
        deleted = ProjectFactory(is_deleted=True)
        project.nodes.append(deleted)
        project.save()

        result = find_nested_projects()
        assert deleted not in result


def main():
    result = find_nested_projects()
    print('Number of nested projects: {0}'.format(len(results)))

if __name__ == '__main__':
    main()
