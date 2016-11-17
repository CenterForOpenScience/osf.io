"""Restores a deleted node.
NOTE: Only use this for nodes that have no addons except for OSFStorage and Wiki.
"""
import logging
import sys

from framework.transactions.context import TokuTransaction
from website.models import Node, NodeLog
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def hide_deleted_logs(node):
    for log in node.logs:
        if log.action in {NodeLog.PROJECT_DELETED, NodeLog.NODE_REMOVED}:
            logger.info('Hiding log {}'.format(log._id))
            log.should_hide = True
            log.save()

def restore_node(node):
    logger.info('Restoring node {}'.format(node._id))
    assert set([e.config.short_name for e in node.get_addons()]) == {'osfstorage', 'wiki'}
    node.is_deleted = False
    node.deleted_date = None
    hide_deleted_logs(node)
    node.save()

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    node_id = sys.argv[1]
    node = Node.load(node_id)
    if not node:
        logger.error('Node "{}" not found'.format(node_id))
        sys.exit(1)

    with TokuTransaction():
        for each in node.node_and_primary_descendants():
            restore_node(each)
        if dry_run:
            raise Exception('Dry Run -- Aborting Transaction')
    logger.info('Finished restoring node {}'.format(node_id))

if __name__ == '__main__':
    main()
