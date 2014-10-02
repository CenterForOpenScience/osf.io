#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Find nodes derived from other nodes that share a piwik_site_id with a parent.

"""

import logging

from modularodm.query.querydialect import DefaultQueryDialect as Q
from nose.tools import *

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import NodeFactory, ProjectFactory, RegistrationFactory, UserFactory
from website.app import init_app
from website.models import Node


logger = logging.getLogger('root')


def has_duplicate_piwik_id(node):
    if node.piwik_site_id is None:
        return False
    return Node.find(Q('piwik_site_id', 'eq', node.piwik_site_id)).count() > 1


def get_broken_registrations():
    return (
        node for node
        in Node.find(Q('is_registration', 'eq', True))
        if has_duplicate_piwik_id(node)
    )


def get_broken_forks():
    return (
        node for node
        in Node.find(Q('is_fork', 'eq', True))
        if has_duplicate_piwik_id(node)
    )


def get_broken_templated():
    return (
        node for node
        in Node.find(Q('template_node', 'ne', None))
        if has_duplicate_piwik_id(node)
    )


def fix_nodes(nodes):
    idx = 0
    for node in nodes:
        node.piwik_site_id = None
        node.save()
        idx += 1
    return idx


def main():
    init_app('website.settings', set_backends=True, routes=True)

    broken_forks = get_broken_forks()
    broken_templated = get_broken_templated()
    broken_registrations = get_broken_registrations()

    if 'dry' in sys.argv:
        if 'list' in sys.argv:
            print("=== Finding broken templated nodes ===")
            for node in broken_templated:
                print(node._id)

            print("=== Finding broken forks ===")
            for node in broken_forks:
                print(node._id)

            print("=== Finding broken registrations ===")
            for node in broken_registrations:
                print(node._id)
        else:
            print("=== Broken nodes ===")
            print("  Templated  :{}".format(len(list(broken_templated))))
            print("  Forked     :{}".format(len(list(broken_forks))))
            print("  Registered :{}".format(len(list(broken_registrations))))
    else:
        print("Templates")
        print("Fixed {} nodes\n".format(
            fix_nodes(get_broken_templated())
        ))

        print("Forks...")
        print("Fixed {} nodes\n".format(
            fix_nodes(get_broken_forks())
        ))

        print("Registrations...")
        print("Fixed {} nodes\n".format(
            fix_nodes(get_broken_registrations())
        ))


class TestMigrateRegistrations(OsfTestCase):
    def setUp(self):
        super(TestMigrateRegistrations, self).setUp()
        # Create registration with correct settings
        self.registration = RegistrationFactory()

        self.registration.registered_from.piwik_site_id = 1
        self.registration.registered_from.save()

        self.registration.piwik_site_id = 2
        self.registration.save()

        # Create registration with duplicated piwik_site_id
        self.broken_registration = RegistrationFactory()

        self.broken_registration.registered_from.piwik_site_id = 3
        self.broken_registration.registered_from.save()

        self.broken_registration.piwik_site_id = 3
        self.broken_registration.save()

    def tearDown(self):
        super(TestMigrateRegistrations, self).tearDown()
        Node.remove()

    def test_get_broken_registrations(self):
        nodes = list(get_broken_registrations())

        assert_equal(1, len(nodes))
        assert_equal(
            self.broken_registration,
            nodes[0]
        )

    def test_fix_registrations(self):
        assert_equal(
            1,
            fix_nodes(get_broken_registrations())
        )

        # invalidate m-odm cache
        Node._clear_caches()

        broken_nodes = list(get_broken_registrations())

        assert_equal(0, len(broken_nodes))
        assert_is_none(
            self.broken_registration.piwik_site_id
        )
        assert_is_not_none(
            self.broken_registration.registered_from.piwik_site_id
        )


class TestMigrateTemplates(OsfTestCase):
    def setUp(self):
        super(TestMigrateTemplates, self).setUp()
        # Create registration with correct settings
        self.user = UserFactory()
        self.consolidated_auth = Auth(user=self.user)

        # Create base project
        self.base_project = ProjectFactory(
            creator=self.user,
            piwik_site_id=1,
        )

        self.base_component = NodeFactory(
            project=self.base_project,
            creator=self.user,
            piwik_site_id=2,
        )

        # Create valid template
        self.template_project = self.base_project.use_as_template(
            auth=self.consolidated_auth
        )
        self.template_project.piwik_site_id = 3
        self.template_project.save()

        self.template_component = self.template_project.nodes[0]
        self.template_component.piwik_site_id = 4
        self.template_component.save()

        # Create broken fork
        self.bad_template_project = self.base_project.use_as_template(
            auth=self.consolidated_auth
        )
        self.bad_template_project.piwik_site_id = self.base_project.piwik_site_id
        self.bad_template_project.save()

        self.bad_template_component = self.bad_template_project.nodes[0]
        self.bad_template_component.piwik_site_id = self.base_component.piwik_site_id
        self.bad_template_component.save()

    def tearDown(self):
        super(TestMigrateTemplates, self).tearDown()
        Node.remove()

    def test_get_broken_templated(self):
        nodes = set(get_broken_templated())

        assert_equal(2, len(nodes))
        assert_equal(
            {self.bad_template_project, self.bad_template_component},
            nodes,
        )

    def test_fix_templated(self):
        assert_equal(
            2,
            fix_nodes(get_broken_templated())
        )

        Node._clear_caches()

        broken_nodes = list(get_broken_templated())

        assert_equal(0, len(broken_nodes))
        assert_is_none(self.bad_template_project.piwik_site_id)
        assert_is_none(self.bad_template_component.piwik_site_id)

        assert_is_not_none(self.template_project.piwik_site_id)
        assert_is_not_none(self.template_component.piwik_site_id)


class TestMigrateForks(OsfTestCase):
    def setUp(self):
        super(TestMigrateForks, self).setUp()
        # Create registration with correct settings
        self.user = UserFactory()
        self.consolidated_auth = Auth(user=self.user)

        # Create base project
        self.base_project = ProjectFactory(
            creator=self.user,
            piwik_site_id=1,
        )

        self.base_component = NodeFactory(
            project=self.base_project,
            creator=self.user,
            piwik_site_id=2,
        )

        # Create valid fork
        self.fork_project = self.base_project.fork_node(
            auth=self.consolidated_auth
        )
        self.fork_project.piwik_site_id = 3
        self.fork_project.save()

        self.fork_component = self.fork_project.nodes[0]
        self.fork_component.piwik_site_id = 4
        self.fork_component.save()

        # Create broken fork
        self.bad_fork_project = self.base_project.fork_node(
            auth=self.consolidated_auth
        )
        self.bad_fork_project.piwik_site_id = self.base_project.piwik_site_id
        self.bad_fork_project.save()

        self.bad_fork_component = self.bad_fork_project.nodes[0]
        self.bad_fork_component.piwik_site_id = self.base_component.piwik_site_id
        self.bad_fork_component.save()

    def tearDown(self):
        super(TestMigrateForks, self).tearDown()
        Node.remove()

    def test_get_broken_forks(self):
        nodes = set(get_broken_forks())

        assert_equal(2, len(nodes))
        assert_equal(
            {self.bad_fork_project, self.bad_fork_component},
            nodes,
        )

    def test_fix_forks(self):
        assert_equal(
            2,
            fix_nodes(get_broken_forks())
        )


        Node._clear_caches()

        broken_nodes = list(get_broken_forks())

        assert_equal(0, len(broken_nodes))
        assert_is_none(self.bad_fork_project.piwik_site_id)
        assert_is_none(self.bad_fork_component.piwik_site_id)

        assert_is_not_none(self.fork_project.piwik_site_id)
        assert_is_not_none(self.fork_component.piwik_site_id)



if __name__ == "__main__":
    main()