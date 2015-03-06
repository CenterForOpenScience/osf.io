#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ensure all projects modified today are consistent between the OSF and Piwik
"""

import datetime
import logging
import sys
import time

from modularodm import Q

from framework.analytics import piwik
from scripts import utils as scripts_utils
from website.app import init_app
from website.project.model import NodeLog


logger = logging.getLogger(__name__)


def get_nodes():
    """Return a set of node with log events for today"""
    today = datetime.date.today()
    midnight = datetime.datetime(
        year=today.year,
        month=today.month,
        day=today.day,
    )

    return set(
        (
            log.node
            for log in NodeLog.find(Q('date', 'gt', midnight))
        )
    )


def main():
    init_app('website.settings', set_backends=True, routes=False)

    if 'dry' in sys.argv:
        if 'list' in sys.argv:
            logger.info('=== Nodes modified today ===')
            for node in get_nodes():
                logger.info(node._id)
        else:
            logger.info('{} Nodes to be updated'.format(len(get_nodes())))
    else:
        # Log to a file
        scripts_utils.add_file_logger(logger, __file__)
        nodes = get_nodes()
        logger.info('=== Updating {} Nodes ==='.format(len(nodes)))
        for node in nodes:
            # Wait a second between requests to reduce load on Piwik
            time.sleep(1)
            piwik._update_node_object(node)
            logger.info(node._id)


if __name__ == "__main__":
    main()
