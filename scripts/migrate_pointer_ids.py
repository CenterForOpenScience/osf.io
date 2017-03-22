"""Changes all _ids for pointers to stringified ObjectIds to prevent clashes with the
GUID collection.
"""
import argparse
import logging

from modularodm import Q

from framework.mongo import ObjectId, database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.models import Pointer


logger = logging.getLogger(__name__)

def remove_invalid_backref(pointer):
    """Remove backref on orphaned pointer, e.g. pointer is not in its parent's
    nodes list.

    :param Pointer pointer
    """
    database['pointer'].update({'_id': pointer._id}, {'$set': {'__backrefs': {}}}, multi=False)

def migrate(dry=True):
    migrated = 0
    pointers_with_invalid_backrefs = []
    pointers = database.pointer.find({'$where': 'this._id.length <= 5'}, {'_id': True})
    total = pointers.count()
    for i, doc in enumerate(pointers):
        pointer = Pointer.load(doc['_id'])
        with TokuTransaction():
            old_id = pointer._id
            logger.info('({}/{}) Preparing to migrate Pointer {}'.format(i + 1, total, old_id))
            pointer._legacy_id = old_id
            pointer._id = str(ObjectId())
            try:
                if not dry:
                    pointer.save()
            except ValueError:
                logger.warn('Removing backref for orphaned pointer: {}'.format(old_id))
                if not dry:
                    remove_invalid_backref(pointer)
                    pointers_with_invalid_backrefs.append(old_id)
                    pointer.save()
            logger.info('Successfully migrated Pointer {} _id to {}'.format(old_id, pointer._id))
            migrated += 1
    logger.info('Successfully migrated {} pointers'.format(migrated))
    logger.info('Removed invalid backrefs on {} pointers: {}'.format(len(pointers_with_invalid_backrefs), pointers_with_invalid_backrefs))

def main():
    parser = argparse.ArgumentParser(
        description='Changes all Pointer _ids to stringified ObjectIDs'
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Run migration and roll back changes to db',
    )
    pargs = parser.parse_args()
    if not pargs.dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    migrate(dry=pargs.dry_run)

if __name__ == '__main__':
    main()
