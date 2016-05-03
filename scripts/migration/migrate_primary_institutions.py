import sys
import logging

from modularodm import Q

from website.app import init_app
from website.models import Node, NodeLog

logger = logging.getLogget(__name__)
logging.basicConfig(level=logging.WARN)

PRIMARY_INSTITUTION_CHANGED = 'primary_institution_changed'
PRIMARY_INSTITUTION_REMOVED = 'primary_institution_removed'

def migrate_logs(dry_run):
    added_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_CHANGED))
    for log in added_logs:
        logger.warn('Log with id <{}> being updated for affiliation added').format(log._id)
        if not dry_run:
            log.action = NodeLog.AFFILIATED_INSTITUTION_ADDED
            log.save()
    removed_logs = NodeLog.find(Q('action', 'eq', PRIMARY_INSTITUTION_REMOVED))
    for log in removed_logs:
        logger.warn('Log with id <{}> being updated for affiliation removed').format(log._id)
        if not dry_run:
            log.action = NodeLog.AFFILIATED_INSTITUTION_REMOVED
            log.save()

def migrate_nodes(dry_run):
    nodes = Node.find(Q('primary_institution', 'ne', None))
    for node in nodes:
        logger.warn('Node with id <{}> and title <{}> being updated').format(node._id, node.title)
        if not dry_run:
            inst = node.primary_institution
            if inst not in node.affiliated_institutions:
                node.affiliated_institutions.append(inst)
            node.primary_institution = None
            node.save()

def main(dry_run=True):
    if dry_run:
        logger.warn('DRY RUN mode')
    migrate_logs(dry_run)
    migrate_nodes(dry_run)

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    app = init_app()
    main(dry_run=dry_run)
