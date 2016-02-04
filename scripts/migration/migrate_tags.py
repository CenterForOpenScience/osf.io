"""Add `lower` field to all tags so that Tags can be queried efficiently"""
import sys
import logging
from website.models import Tag
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)


def do_migration():
    for t in Tag.find():
        logger.info('Migrating tag {!r}'.format(t))
        t.lower = t._id.lower()
        t.save(force=True)


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models

    # Start a transaction that will be rolled back if any exceptions are un
    with TokuTransaction():
        do_migration()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Allow setting the log level just by appending the level to the command
    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    # Finally run the migration
    main(dry=dry)
