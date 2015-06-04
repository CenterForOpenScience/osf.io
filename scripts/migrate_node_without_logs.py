# -*- coding: utf-8 -*-
"""Backup and remove nodes with no logs.
"""

import logging

from modularodm import Q

from website import models
from website.app import init_app

from scripts.utils import (
    backup_node_git, backup_node_mongo
)

logger = logging.getLogger(__name__)


def find_nodes_without_logs():
    return models.Node.find(Q('logs.0', 'exists', False) & Q('is_deleted', 'ne', True))


def migrate_node(node, dry_run=True):
    logger.warn('Backing up and removing node {0}'.format(node._id))
    if not dry_run:
        backup_node_git(node)
        backup_node_mongo(node)


def main(dry_run=True):
    init_app()
    nodes_without_logs = find_nodes_without_logs()
    logger.warn(
        'Found {0} nodes with no logs'.format(
            nodes_without_logs.count()
        )
    )
    for node in nodes_without_logs:
        migrate_node(node, dry_run=dry_run)


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    main(dry_run=dry)