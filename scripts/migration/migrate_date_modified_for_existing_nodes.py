"""
This will add a date_modified field to all nodes.  Date_modified will be equivalent to the date of the last log.
"""
import sys
import logging

from website import models
from website.app import init_app

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    logger.warn('Date_modified field will be added to all nodes.')
    if dry_run:
        logger.warn('Dry_run mode')
    for node in models.Node.find():
        logger.info('Node {0} "date_modified" added'.format(node._id))
        if not dry_run:
            node.date_modified = node.date_updated()
            node.save()

if __name__ == '__main__':
    main()
