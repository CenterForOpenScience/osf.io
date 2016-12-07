import sys
import logging

from modularodm import Q

from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.project.model import Node, NodeLog


logger = logging.getLogger(__name__)


# This is where all your migration log will go
def do_migration():
    dupe_nodes = [n for n in Node.find(Q('_id', 'in', list(set([l.node._id for l in NodeLog.find(Q('action', 'eq', 'preprint_license_updated'))])))) if NodeLog.find(Q('action', 'eq', 'preprint_license_updated') & Q('node', 'eq', n._id)).count() > 1]
    logger.info('Found {} nodes with multiple preprint_license_updated logs'.format(len(dupe_nodes)))

    for node in dupe_nodes:
        preprint_license_updated_logs = [log for log in node.logs if log.action == 'preprint_license_updated']

        log = preprint_license_updated_logs.pop()
        while(preprint_license_updated_logs):
            next_log = preprint_license_updated_logs.pop()
            timedelta = log.date - next_log.date
            if timedelta.seconds < 60:
                logger.info(
                    'Hiding duplicate preprint_license_updated log with ID {} from node {}, timedelta was {}'.format(
                        log._id, node._id, timedelta
                    )
                )
                log.should_hide = True
                log.save()
            else:
                logger.info(
                    'Skipping preprint_license_updated log with ID {} from node {}, timedelta was {}'.format(
                        log._id, node._id, timedelta
                    )
                )

            log = next_log


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models

    # Start a transaction that will be rolled back if any exceptions are un
    with TokuTransaction():
        do_migration()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
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
