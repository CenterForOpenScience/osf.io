import logging
import sys

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import NodeLog, PreprintService
from scripts import utils as script_utils
from modularodm import Q
from modularodm.exceptions import NoResultsFound

logger = logging.getLogger(__name__)


def migrate(dry_run=True):
    node_logs = list(NodeLog.find(
        Q('action', 'in', [NodeLog.PREPRINT_FILE_UPDATED, NodeLog.PREPRINT_INITIATED]) &
        Q('params.preprint', 'exists', False)
    ))

    logger.info('Preparing to migrate {} NodeLogs'.format(len(node_logs)))

    count = 0

    for log in node_logs:
        preprint = None
        node_id = log.params.get('node')

        try:
            preprint = PreprintService.find_one(Q('node', 'eq', node_id))
        except NoResultsFound:
            logger.error('Skipping {}, preprint not found for node: {}'.format(log._id, node_id))
            continue

        logger.info(
            'Migrating log - {} - to add params.preprint: {}, '.format(log._id, preprint._id)
        )

        log.params['preprint'] = preprint._id
        log.save()
        count += 1

    logger.info('Migrated {} logs'.format(count))

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')


if __name__ == '__main__':
    main()
