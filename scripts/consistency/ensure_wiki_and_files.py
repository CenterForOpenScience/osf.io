#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adds wiki and osffiles addons to nodes that do not have them.

Log:

    Performed on production by sloria on 2014-08-19 at 4:55PM (EST). 2008 projects
    without the OSF File Storage Addon were migrated. 2 projects without the
    OSF Wiki addon were migrated.
"""

import logging

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import NodeFactory

from website.app import init_app
from website.project.model import Node

from website.addons.wiki.model import AddonWikiNodeSettings
from website.addons.osffiles.model import AddonFilesNodeSettings

logger = logging.getLogger(__name__)

ADDONS = {AddonFilesNodeSettings, AddonWikiNodeSettings}


def main():
    from framework.mongo import db
    init_app(routes=False)
    migrate_nodes(db)


def migrate_addons(node):
    ret = False
    if not node.has_addon('wiki'):
        node.add_addon('wiki', auth=node.creator, log=False)
        ret = True
    if not node.has_addon('osffiles'):
        node.add_addon('osffiles', auth=node.creator, log=False)
        ret = True
    return ret


def migrate_nodes(db):
    for addon_class in ADDONS:
        print('Processing ' + addon_class.__name__)

        for node in get_affected_nodes(db, addon_class):
            print(' - ' + node._id)
            migrate_addons(node)

        print('')

    print('-----\nDone.')


def get_affected_nodes(db, addon_class):
    """Generate affected nodes."""
    query = db['node'].find({
        '.'.join(
            ('__backrefs',
                'addons',
                addon_class.__name__.lower(),
                'owner',
                '0'
            )
        ): {'$exists': False}
    })
    return (Node.load(node['_id']) for node in query)


class TestMigratingAddons(OsfTestCase):

    def test_migrate_wiki(self):
        node = NodeFactory()
        wiki_addon = node.get_addon('wiki')
        AddonWikiNodeSettings.remove_one(wiki_addon)
        assert_false(node.has_addon('wiki'))
        was_migrated = migrate_addons(node)
        assert_true(was_migrated)
        assert_true(node.has_addon('wiki'))

    def test_migrate_osffiles(self):
        node = NodeFactory()
        osf_addon = node.get_addon('osffiles')
        AddonFilesNodeSettings.remove_one(osf_addon)
        assert_false(node.has_addon('osffiles'))
        was_migrated = migrate_addons(node)
        assert_true(was_migrated)
        assert_true(node.has_addon('osffiles'))

    def test_no_migration_if_addon_exists(self):
        node = NodeFactory()
        assert_true(node.has_addon('wiki'))
        assert_true(node.has_addon('osffiles'))
        migrate_nodes(self.db)
        assert_false(migrate_addons(node))

    def test_affected_nodes(self):
        affected_node = NodeFactory()
        AddonWikiNodeSettings.remove_one(affected_node.get_addon('wiki'))
        assert_false(affected_node.has_addon('wiki'))

        unaffected_node = NodeFactory()
        assert_true(unaffected_node.has_addon('wiki'))

        affected_nodes = list(get_affected_nodes(self.db, AddonWikiNodeSettings))

        assert_in(affected_node, affected_nodes)
        assert_not_in(unaffected_node, affected_nodes)


if __name__ == '__main__':
    main()
