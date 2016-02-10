# -*- coding: utf-8 -*-
import sys
import logging

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import NodeLog, Node
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)

# Use a system to mark migrated nodes
SYSTEM_TAG = 'migrated_logs'

def get_all_parents(node):
    # return a list contains all possible forked_from and registered_from of the node to the very origin
    parent_list = []
    while True:
        parent = get_parent(node)
        if parent is None:
            break
        parent_list.append(parent)
        node = parent
    return parent_list


def get_parent(node):
    # detemine the latest action of the node that generate this node and return its parent
    if node.forked_from and node.registered_from:
        if node.forked_date > node.registered_date:
            return node.forked_from
        else:
            return node.registered_from
    elif node.forked_from and not node.registered_from:
        return node.forked_from
    elif node.registered_from and not node.forked_from:
        return node.registered_from
    else:
        return None


def do_migration(records, dry=False):
    for node in records:
        logs = list(NodeLog.find(Q('was_connected_to', 'eq', node)))
        existing_logs = node.logs
        for log in logs:
            if not log.node__logged:
                continue
            log_node = log.node__logged[0]
            # if the log_node is not contained in the node parent list then it doesn't belong to this node
            if log_node not in get_all_parents(node):
                logger.info('Excluding log {} from list because it is not associated with node {}'.format(log, node))
                logs.remove(log)

        with TokuTransaction():
            node.logs = logs + existing_logs
            node.system_tags.append(SYSTEM_TAG)
            node_type = 'registration' if node.is_registration else 'fork'
            logger.info('Adding {} logs to {} {}'.format(len(logs), node_type, node))
            if not dry:
                try:
                    node.save()
                except Exception as err:
                    logger.error('Could not update logs for node {} due to error'.format(node._id))
                    logger.exception(err)
                    logger.error('Skipping...')


def get_targets():
    return Node.find(
        (
            (Q('registered_from', 'ne', None) & Q('logs', 'eq', []))
            | Q('forked_from', 'ne', None)
        )
        & Q('is_deleted', 'ne', True)
        & Q('system_tags', 'ne', SYSTEM_TAG)
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
