#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Find nodes derived from other nodes that share a piwik_site_id with a parent.

Log:

    Run by sloria on 2015-02-24 at 12:04PM EST. A log was saved to /opt/data/migration-logs.
"""

import json
import logging
import sys

from modularodm import Q
import requests

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import NodeFactory, ProjectFactory, RegistrationFactory, UserFactory
from website.app import init_app
from website.models import Node
from website.settings import PIWIK_ADMIN_TOKEN, PIWIK_HOST
from scripts import utils as scripts_utils

logger = logging.getLogger('root')


class PiwikSiteCache(object):
    def __init__(self):
        self._cache = None

    def update_cache(self):
        self._cache = requests.get('{host}index.php?module=API&method=SitesManager.getAllSites&format=JSON&token_auth={auth_token}'.format(
            host=PIWIK_HOST,
            auth_token=PIWIK_ADMIN_TOKEN,
        )).json()

    def node_has_duplicate_piwik_id(self, node):
        if not self._cache:
            self.update_cache()

        try:
            piwik_alias = self._cache[str(node.piwik_site_id)].get('name')
        except KeyError:
            return False

        if not piwik_alias:
            return False
        return not piwik_alias[6:] == node._id


piwik_cache = PiwikSiteCache()


def has_duplicate_piwik_id(node):
    if node.piwik_site_id is None:
        return False
    return piwik_cache.node_has_duplicate_piwik_id(node)


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
        logger.info('Setting piwik_site_id to None for Node {}'.format(node._id))
        node.piwik_site_id = None
        node.save()
        idx += 1
    return idx


def main():
    init_app('website.settings', set_backends=True, routes=False)

    broken_forks = get_broken_forks()
    broken_templated = get_broken_templated()
    broken_registrations = get_broken_registrations()

    if 'dry' in sys.argv:
        if 'list' in sys.argv:
            logger.info("=== Finding broken templated nodes ===")
            for node in broken_templated:
                logger.info(node._id)

            logger.info("=== Finding broken forks ===")
            for node in broken_forks:
                logger.info(node._id)

            logger.info("=== Finding broken registrations ===")
            for node in broken_registrations:
                logger.info(node._id)
        else:
            logger.info("=== Broken nodes ===")
            logger.info("  Templated  :{}".format(len(list(broken_templated))))
            logger.info("  Forked     :{}".format(len(list(broken_forks))))
            logger.info("  Registered :{}".format(len(list(broken_registrations))))
    else:
        # Log to a file
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Templates")
        logger.info("Fixed {} nodes\n".format(
            fix_nodes(broken_templated)
        ))

        logger.info("Forks...")
        logger.info("Fixed {} nodes\n".format(
            fix_nodes(broken_forks)
        ))

        logger.info("Registrations...")
        logger.info("Fixed {} nodes\n".format(
            fix_nodes(broken_registrations)
        ))


from nose.tools import *  # noqa
import responses


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

        responses.start()
        responses.add(
            responses.GET,
            '{host}index.php?module=API&method=SitesManager.getAllSites&format=JSON&token_auth={auth_token}'.format(
                host=PIWIK_HOST,
                auth_token=PIWIK_ADMIN_TOKEN,
            ),
            status=200,
            content_type='application/json',
            body=json.dumps({
                '1': {'name': 'Node: ' + self.registration.registered_from._id},
                '2': {'name': 'Node: ' + self.registration._id},
                '3': {'name': 'Node: ' + self.broken_registration.registered_from._id},
                '4': {'name': 'Node: ' + self.broken_registration._id},
            }),
            match_querystring=True,
        )

    def tearDown(self):
        super(TestMigrateRegistrations, self).tearDown()
        Node.remove()
        responses.stop()
        responses.reset()
        piwik_cache._cache = None

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

        responses.start()
        responses.add(
            responses.GET,
            '{host}index.php?module=API&method=SitesManager.getAllSites&format=JSON&token_auth={auth_token}'.format(
                host=PIWIK_HOST,
                auth_token=PIWIK_ADMIN_TOKEN,
            ),
            status=200,
            content_type='application/json',
            body=json.dumps({
                '1': {'name': 'Node: ' + self.base_project._id},
                '2': {'name': 'Node: ' + self.base_component._id},
                '3': {'name': 'Node: ' + self.template_project._id},
                '4': {'name': 'Node: ' + self.template_component._id},
            }),
            match_querystring=True,
        )

    def tearDown(self):
        super(TestMigrateTemplates, self).tearDown()
        Node.remove()
        responses.stop()
        responses.reset()
        piwik_cache._cache = None

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

        responses.start()
        responses.add(
            responses.GET,
            '{host}index.php?module=API&method=SitesManager.getAllSites&format=JSON&token_auth={auth_token}'.format(
                host=PIWIK_HOST,
                auth_token=PIWIK_ADMIN_TOKEN,
            ),
            status=200,
            content_type='application/json',
            body=json.dumps({
                '1': {'name': 'Node: ' + self.base_project._id},
                '2': {'name': 'Node: ' + self.base_component._id},
                '3': {'name': 'Node: ' + self.fork_project._id},
                '4': {'name': 'Node: ' + self.fork_component._id},
            }),
            match_querystring=True,
        )

    def tearDown(self):
        super(TestMigrateForks, self).tearDown()
        Node.remove()
        responses.stop()
        responses.reset()
        piwik_cache._cache = None

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
