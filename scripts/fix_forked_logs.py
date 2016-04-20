# -*- coding: utf-8 -*-
import sys
import logging

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website import models
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def migrate():
    migrated = []
    invalid = []

    expected_count = models.NodeLog.find(
        Q('action', 'eq', models.NodeLog.NODE_FORKED) &
        Q('params.registration', 'eq', None)
    ).count()

    logger.info('Expecting to migrate {} logs'.format(expected_count))

    for fork in models.Node.find(Q('is_fork', 'eq', True)):
        logger.info('Migrating fork: {}'.format(fork._id))
        try:
            forked_log = next(
                e for e in fork.logs if
                e and e.action == models.NodeLog.NODE_FORKED and
                e.date == fork.forked_date
            )
        except StopIteration:
            logger.warn('Skipping fork that has no "node_forked" log: {}'.format(fork._id))
            invalid.append(fork)

        if not forked_log.params.get('registration'):
            forked_log.params['registration'] = fork._primary_key
            logger.info('  * Set "registration" param on Log {} to {}'.format(forked_log._id, fork._id))
            forked_log.save()
            migrated.append(fork._id)

    if invalid:
        logger.warn('Skipped {} forks that have no "node_forked" log'.format(len(invalid)))
        logger.warn([each._id for each in invalid])

    logger.info('Migrated {} logs'.format(len(migrated)))

    unmigrated = models.NodeLog.find(
        Q('action', 'eq', models.NodeLog.NODE_FORKED) &
        Q('params.registration', 'eq', None)
    )

    logger.warn([e._id for e in unmigrated])
    if unmigrated.count():
        logger.warn('Skipped {} log(s) that have no forward ref pointing to it'.format(unmigrated.count()))
        logger.warn([each._id for each in unmigrated])

def main():
    init_app(routes=False)
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == "__main__":
    main()
