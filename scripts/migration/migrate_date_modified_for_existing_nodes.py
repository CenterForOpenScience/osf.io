"""
This will add a date_modified field to all nodes.  Date_modified will be equivalent to the date of the last log.
"""
import sys
import logging
from website.app import init_app
from website import models
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)

def date_updated(node):
    """
    The most recent datetime when this node was modified, based on
    the logs.
    """
    try:
        return node.logs[-1].date
    except IndexError:
        return node.date_created

def main():
    init_app(routes=False)

    logger.warn('Date_modified field will be added to all nodes.')

    for node in models.Node.find():
        node.date_modified = date_updated(node)
        node.save()
        logger.info('Node {0} "date_modified" added'.format(node._id))


if __name__ == '__main__':

    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    with TokuTransaction():
        main()
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')




