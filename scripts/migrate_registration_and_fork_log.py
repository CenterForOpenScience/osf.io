# -*- coding: utf-8 -*-
import sys
import logging

from website.app import init_app
from website.models import NodeLog, Node
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def get_all_parents(node):
    # return a list contains all possible forked_from and registered_from of the node to the very origin
    parent_list = []
    while True:
        if get_parent(node) is None:
            return False
        if get_parent(node):
            parent_list.append(get_parent(node))
            return True
        node = get_parent(node)
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
        logs = list(NodeLog.find(Q('was_connected_to', 'contains', node)))

        for log in logs:
            log_node = log.node__logged[0]
            # if the log_node is not contained in the node parent list then it doesn't belong to this node
            if log_node not in get_all_parents(node):
                logger.info('Removing log {} from list because it is not associated with node {}'.format(log, node))
                logs.remove(log)

        node.logs = logs
        logger.info('Adding {} logs to {}'.format(len(logs), node))
        if not dry:
            node.save()


def get_targets():
    return Node.find(
        (
            (Q('registered_from', 'ne', None) & Q('logs', 'eq', []))
            | Q('forked_from', 'ne', None)
        )
        & Q('is_deleted', 'ne', True)
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()