#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Update Piwik for nodes that were forked, registered or templated prior to
October 2014.
"""

import datetime
import logging
import sys
import time

from modularodm import Q

from framework.analytics.piwik import _update_node_object
from scripts import utils as scripts_utils
from website.app import init_app
from website.models import Node


logger = logging.getLogger('root')


def get_nodes():
    forked = Q('__backrefs.forked.node.forked_from', 'ne', None)
    registered = Q('__backrefs.registrations.node.registered_from', 'ne', None)
    templated = Q('__backrefs.template_node.node.template_node', 'ne', None)
    duplicate = (forked | registered | templated)

    return Node.find(
        duplicate and Q('date_created', 'lt', datetime.datetime(2014, 10, 31))
    )


def main():
    init_app('website.settings', set_backends=True, routes=False)

    if 'dry' in sys.argv:
        if 'list' in sys.argv:
            logger.info('=== Nodes ===')
            for node in get_nodes():
                logger.info(node._id)
        else:
            logger.info('{} Nodes to be updated'.format(get_nodes().count()))
    else:
        # Log to a file
        scripts_utils.add_file_logger(logger, __file__)
        nodes = get_nodes()
        logger.info('=== Updating {} Nodes ==='.format(nodes.count()))
        for node in nodes:
            # Wait a second between requests to reduce load on Piwik
            time.sleep(1)
            logger.info('Calling _update_node_objecton Node {}'.format(node._id))
            _update_node_object(node)
    logger.info('Finished')


if __name__ == "__main__":
    main()
