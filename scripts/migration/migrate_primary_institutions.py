import sys
import logging

from modularodm import Q

from framework.transactions.context import TokuTransaction

from scripts import utils
from website.app import init_app
from website.models import Node, NodeLog

logger = logging.getLogger(__name__)
logging.basicConfig()

PRIMARY_INSTITUTION_CHANGED = 'primary_institution_changed'
PRIMARY_INSTITUTION_REMOVED = 'primary_institution_removed'

def migrate(dry_run=True):
    added_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_CHANGED))
    for log in added_logs:
        logger.info('Log with id <{}> being updated for affiliation added'.format(log._id))
        log.action = NodeLog.AFFILIATED_INSTITUTION_ADDED
        log.save()

    removed_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_REMOVED))
    for log in removed_logs:
        logger.info('Log with id <{}> being updated for affiliation removed'.format(log._id))
        log.action = NodeLog.AFFILIATED_INSTITUTION_REMOVED
        log.save()

    nodes = Node.find(Q('primary_institution', 'ne', None))
    for node in nodes:
        logger.info('Node with id <{}> and title <{}> being updated'.format(node._id, node.title))
        inst = node.primary_institution
        if inst not in node.affiliated_institutions:
            node.affiliated_institutions.append(inst)
        node.primary_institution = None
        node.save()
    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def main():
    dry_run = 'dry' in sys.argv
    if dry_run:
        logger.warn('DRY RUN mode')
    else:
        utils.add_file_logger(logger, __file__)
    init_app(routes=False)
    with TokuTransaction():
        migrate(dry_run)

if __name__ == '__main__':
    main()
