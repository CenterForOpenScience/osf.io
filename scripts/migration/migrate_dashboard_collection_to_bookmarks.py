import logging
import sys

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def migrate():
    logger.info('migrating folders to collections and dashboards to bookmarks')

    logger.info('is_folder -> is_collection')
    database.node.update({
        'is_folder': {'$ne': None}
    }, {
        '$rename': {'is_folder': 'is_collection'}
    }, multi=True)

    logger.info('is_dashboard -> is_bookmark_collection')
    database.node.update({
        'is_dashboard': {'$ne': None}
    }, {
        '$rename': {'is_dashboard': 'is_bookmark_collection'}
    }, multi=True)

    logger.info('Title: `Dashboard` -> `Bookmarks`')
    database.node.update({
        'is_bookmark_collection': True
    }, {
        '$set': {'title': 'Bookmarks'}
    }, multi=True)


def reverse_migration():
    logger.info('migrating collections to folders and bookmarks to dashboards')

    logger.info('is_collection -> is_folder')
    database.node.update({
        'is_collection': {'$ne': None}
    }, {
        '$rename': {'is_collection': 'is_folder'}
    }, multi=True)

    logger.info('is_bookmark_collection -> is_dashboard')
    database.node.update({
        'is_bookmark_collection': {'$ne': None}
    }, {
        '$rename': {'is_bookmark_collection': 'is_dashboard'}
    }, multi=True)

    logger.info('Title: `Bookmarks` -> `Dashboard`')
    database.node.update({
        'is_dashboard': True
    }, {
        '$set': {'title': 'Dashboard'}
    }, multi=True)

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    script_utils.add_file_logger(logger, __file__)

    if 'reverse' in sys.argv:
        with TokuTransaction():
            reverse_migration()
    else:
        with TokuTransaction():
            migrate()
