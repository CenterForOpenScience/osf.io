import logging

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app

logger = logging.getLogger(__name__)


def migrate():
    logger.info('migrating folders to collections and dashboards to bookmarks')

    logger.info('is_folder -> is_collection')
    bulk.find({
        'is_folder': {'$ne': None}
    }).update({
        '$rename': {'is_folder': 'is_collection'}
    })

    logger.info('is_dashboard -> is_bookmark_collection')
    bulk.find({
        'is_dashboard': {'$ne': None}
    }).update({
        '$rename': {'is_dashboard': 'is_bookmark_collection'}
    })

    logger.info('Title: `Dashboard` -> `Bookmarks`')
    bulk.find({
        'is_bookmark_collection': True
    }).update({
        '$set': {'title': 'Bookmarks'}
    })


def reverse_migration():
    logger.info('migrating collections to folders and bookmarks to dashboards')

    logger.info('is_collection -> is_folder')
    bulk.find({
        'is_collection': {'$ne': None}
    }).update({
        '$rename': {'is_collection': 'is_folder'}
    })

    logger.info('is_bookmark_collection -> is_dashboard')
    bulk.find({
        'is_bookmark_collection': {'$ne': None}
    }).update({
        '$rename': {'is_bookmark_collection': 'is_dashboard'}
    })

    logger.info('Title: `Bookmarks` -> `Dashboard`')
    bulk.find({
        'is_dashboard': True
    }).update({
        '$set': {'title': 'Dashboard'}
    })

if __name__ == '__main__':
    import sys
    init_app(set_backends=True, routes=False)
    bulk = database.node.initialize_ordered_bulk_op()

    if 'reverse' in sys.argv:
        with TokuTransaction():
            reverse_migration()
    else:
        with TokuTransaction():
            migrate()
