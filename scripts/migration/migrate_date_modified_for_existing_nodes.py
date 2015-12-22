"""
This will add a date_modified field to all nodes.  Date_modified will be equivalent to the date of the last log.
"""
import sys
import logging
from modularodm import Q
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

def main(dry=True):
    init_app(routes=False)
    nodes = models.Node.find(Q('date_modified', 'eq', None))
    node_count = nodes.count()
    count = 0
    errored_nodes = []
    for node in nodes:
        count += 1
        with TokuTransaction():
            node.date_modified = date_updated(node)
            if not dry:
                try:
                    node.save()
                except KeyError as error:  # Workaround for node whose files were not migrated long ago
                    logger.error('Could not migrate node due to error')
                    logger.exception(error)
                    errored_nodes.append(node)
                else:
                    logger.info('{}/{} Node {} "date_modified" added'.format(count, node_count, node._id))

    if errored_nodes:
        logger.error('{} errored'.format(len(errored_nodes)))
        logger.error('\n'.join([each._id for each in errored_nodes]))

if __name__ == '__main__':

    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry_run)
