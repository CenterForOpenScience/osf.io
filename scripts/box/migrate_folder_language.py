import logging
import sys

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from addons.box.model import BoxNodeSettings
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def migrate(dry_run=False):
    bns_collection = database['boxnodesettings']
    migrated_names = {b['_id'] for b in bns_collection.find({'folder_name': 'All Files'})}
    migrated_paths = {b['_id'] for b in bns_collection.find({'folder_path': 'All Files'})}
    assert migrated_names == migrated_paths
    logger.info('Migrating {} BoxNodeSettings documents: {}'.format(len(migrated_names), list(migrated_names)))
    bns_collection.find_and_modify(
        {'folder_name': 'All Files'},
        {'$set': {
            'folder_path': '/',
            'folder_name': '/ (Full Box)'
        }
    })

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == "__main__":
    main()
