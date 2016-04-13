import logging

from modularodm import Q

from website.models import NodeLog
from website.app import init_app

from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_targets():
    logs = NodeLog.find(
            Q('action', 'eq', 'embargo_approved') |
            Q('action', 'eq', 'embargo_initiated') |
            Q('action', 'eq', 'retraction_approved') |
            Q('action', 'eq', 'retraction_initiated') |
            Q('action', 'eq', 'registration_initiated')
    )
    return logs


def migrate_log(logs):
    for log in logs:
        if log.node.registered_from:
            log.params['node'] = log.node.registered_from_id
        else:
            log.params['node'] = log.node.logs[0].node._id
        log.save()
        logger.info('Finished migrate log {}: registration action {} of node {}'.format(log._id, log.action, log.node))


def main(dry_run):
    logs = get_targets()
    migrate_log(logs)
    if not dry_run:
        logger.info('Finished migrate {} logs '.format(len(logs)))
    else:
        raise RuntimeError('Dry Run -- Transaction rolled back')


if __name__ == '__main__':
    import sys
    script_utils.add_file_logger(logger, __file__)
    dry_run = 'dry' in sys.argv
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        main(dry_run=dry_run)