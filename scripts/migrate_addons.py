import logging

from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import NodeFactory

from website.app import init_app
from website.project.model import Node

logger = logging.getLogger(__name__)


def main():
    init_app()
    migrate_nodes()

def migrate_addons(node):
    ret = False
    if not node.has_addon('wiki'):
        node.add_addon('wiki', auth=node.creator, log=False)
        ret = True
    if not node.has_addon('osffiles'):
        node.add_addon('osffiles', auth=node.creator, log=False)
        ret = True
    return ret

def migrate_nodes():
    migrated_count = 0
    nodes = []
    for node in Node.find():
        was_migrated = migrate_addons(node)
        if was_migrated:
            node.save()
            nodes.append(node)
            logger.info('Migrated {0}'.format(node._id))
            migrated_count += 1
    logger.info('Finished migrating {0} nodes.'.format(migrated_count))
    return nodes


class TestMigratingAddons(OsfTestCase):

    def test_migrate_wiki(self):
        node = NodeFactory()
        (node.get_addon('wiki')).delete(save=True)
        assert_false(node.has_addon('wiki'))
        was_migrated = migrate_addons(node)
        assert_true(was_migrated)
        node.save()
        assert_true(node.has_addon('wiki'))

    def test_migrate_osffiles(self):
        node = NodeFactory()
        (node.get_addon('osffiles')).delete(save=True)
        assert_false(node.has_addon('osffiles'))
        was_migrated = migrate_addons(node)
        assert_true(was_migrated)
        node.save()
        assert_true(node.has_addon('osffiles'))

    def test_no_migration_if_addon_exists(self):
        node = NodeFactory()
        assert_true(node.has_addon('wiki'))
        assert_true(node.has_addon('osffiles'))
        was_migrated = migrate_addons(node)
        assert_false(was_migrated)

if __name__ == '__main__':
    main()

