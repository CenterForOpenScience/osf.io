""" Script for removing nodes with 'qatest' tags from elastic search index """
import logging
import sys

import django
django.setup()

from website.app import init_app
from django.db.models import Q
from osf.models import AbstractNode

logger = logging.getLogger(__name__)

def remove_search_index(dry_run=True):
    nodes = AbstractNode.objects.filter(Q(tags__name = 'qatest'))
    if dry_run:
        logger.warn('Dry run mode.')
        for node in nodes:
            logger.info('Removing {} with title \'{}\' from search index.'.format(node._id, node.title))
    else:
        for node in nodes:
            node.delete_search_entry()

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    init_app(routes=False)
    remove_search_index(dry_run=dry_run)