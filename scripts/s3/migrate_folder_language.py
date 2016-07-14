import logging
import sys

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def migrate(dry_run=False):
    sns_collection = database['s3nodesettings']
    logger.info('Migrating all {} S3NodeSettings documents: {}'.format(
        sns_collection.count(), [s['_id'] for s in sns_collection.find()]
    ))
    sns_collection.find_and_modify(
        {},
        {'$rename': {'bucket': 'folder_id'}
    })

    # TODO: update folder_name with bucket location

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
