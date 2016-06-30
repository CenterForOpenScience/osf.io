# -*- coding: utf-8 -*-
"""Ensure all projects have a Piwik node."""
import logging
import time
import sys

from modularodm import Q

from framework.analytics import piwik
from scripts import utils as scripts_utils
from website.app import init_app
from website.models import Node


logger = logging.getLogger(__name__)

def main():
    init_app(set_backends=True, routes=False)
    dry = '--dry' in sys.argv
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)

    nodes = Node.find(Q('piwik_site_id', 'eq', None))
    count = nodes.count()
    for node in nodes:
        logger.info('Provisioning Piwik node for Node {}'.format(node._id))
        if not dry:
            piwik._provision_node(node._id)
            # Throttle to reduce load on Piwik
            time.sleep(1)
    logger.info('Provisioned {} nodes'.format(count))


if __name__ == '__main__':
    main()
