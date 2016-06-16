#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from tests.base import OsfTestCase
from tests.factories import NodeFactory

from website.app import init_app
from website.project.model import Node
from website import settings

logger = logging.getLogger(__name__)

# legacy => new category
MIGRATE_MAP = {
    'category': '',
    'measure': 'methods and measures',
}

def main():
    init_app()
    migrate_nodes()

def migrate_category(node):
    """Migrate legacy, invalid category to new, valid category. Return whether
    the node was changed.
    """
    if node.category not in settings.NODE_CATEGORY_MAP.keys():  # invalid category
        node.category = MIGRATE_MAP.get(node.category, 'other')
        return True
    return False


def migrate_nodes():
    migrated_count = 0
    for node in Node.find():
        was_migrated = migrate_category(node)
        if was_migrated:
            node.save()
            logger.info('Migrated {0}'.format(node._id))
            migrated_count += 1
    logger.info('Finished migrating {0} nodes.'.format(migrated_count))


class TestMigratingCategories(OsfTestCase):

    def test_migrate_category(self):
        node = NodeFactory(category='category')
        was_migrated = migrate_category(node)
        assert was_migrated is True
        node.save()
        assert node.category == ''

    def test_migrate_measure(self):
        node = NodeFactory(category='measure')
        migrate_category(node)
        node.save()
        assert node.category == 'methods and measures'

    def test_everything_else_is_migrated_to_other(self):
        node1 = NodeFactory(category='background')
        migrate_category(node1)
        node1.save()
        assert node1.category == 'other'

        node2 = NodeFactory(category=u'プロジェクト')
        migrate_category(node2)
        node2.save()
        assert node2.category == 'other'

    def test_valid_categories_not_migrated(self):
        node1 = NodeFactory(category='project')
        node2 = NodeFactory(category='hypothesis')

        was_migrated1 = migrate_category(node1)
        was_migrated2 = migrate_category(node2)

        node1.save()
        node2.save()

        assert was_migrated1 is False
        assert was_migrated2 is False
        assert node1.category == 'project'
        assert node2.category == 'hypothesis'

class TestMigrateAll(OsfTestCase):

    def test_migrate_categories_all(self):
        n1 = NodeFactory(category='hypothesis')
        n2 = NodeFactory(category='category')

        migrate_nodes()

        assert n1.category == 'hypothesis'
        assert n2.category == ''

if __name__ == '__main__':
    main()
