# -*- coding: utf-8 -*-

import logging
import sys

from modularodm import Q

from website.app import init_app
from website.project.mailing_list import full_update
from website.project.model import Node


logger = logging.getLogger(__name__)


def main(dry_run=True):
    updated_nodes = Node.find(Q('mailing_updated', 'eq', True))
    for node in updated_nodes:
        migrate_node(node, dry_run)


def migrate_node(node, dry_run=True):
    result = True
    if not dry_run:
        result = full_update(node)
    if result:
        logger.info('Successfully updated node {}'.format(node))
        node.mailing_updated = False
        if not dry_run:
            node.save()
    else:
        logger.error('Did not successfully update node {} due to an HTTP or connection error'.format(node))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
