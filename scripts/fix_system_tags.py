# -*- coding: utf-8 -*-
"""Add system tags that weren't added during the Toku->Postgres migration.
Pass a path to a JSON file that has node IDs as keys and lists of system tag names
as values.
"""
import sys
import logging
import json
from website.app import setup_django
setup_django()
from osf.models import AbstractNode

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main(dry=True):
    systagfile = sys.argv[1]
    with open(systagfile, 'r') as fp:
        systag_data = json.load(fp)
        for node_id, systags in systag_data.iteritems():
            node = AbstractNode.load(node_id)
            for systag in systags:
                logger.info('Adding {} as a system tag to AbstractNode {}'.format(systag, node._id))
                if not dry:
                    node.add_system_tag(systag, save=True)

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
