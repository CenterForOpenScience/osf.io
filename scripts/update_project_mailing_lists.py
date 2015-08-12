# -*- coding: utf-8 -*-

import logging
import sys

from modularodm import Q

from website.app import init_app
from website.project.mailing_list import full_update
from website.project.model import Node


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    updated_nodes = Node.find(Q('mailing_updated', 'eq', True))
    for node in updated_nodes:
        update_node(node, dry_run)


def update_node(node, dry_run=True):

    # reload the node to ensure that it is current
    node.reload()

    # Reset mailing_updated now in case of another user update during this automated one
    node.mailing_updated = False
    if not dry_run:
        node.save()

    try:
        if not dry_run:
            full_update(node)
    except Exception as err:
        logger.error(
            'Unexpected error raised when updating list of '
            'node {}. Continuing...'.format(node))
        logger.exception(err)
        node.mailing_updated = True
        if not dry_run:
            node.save()
    else:
        logger.info('Successfully updated node {}'.format(node))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
