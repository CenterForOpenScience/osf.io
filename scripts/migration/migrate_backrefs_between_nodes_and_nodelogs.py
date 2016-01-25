"""
This migration will add original_node and node associated with the log to nodelogs. It will then make
copies of each nodelog for the remaining nodes in the backref (registrations and forks),
changing the node to the current node.
"""

import sys
import logging
from modularodm import Q
from website.app import init_app
from website import models
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)


def get_original_node(log):
    """
    Retrieves original node on nodelog
    """
    return models.Node.find(Q('_id', 'eq', log._backrefs['logged']['node']['logs'][0]))[0]


def main(dry=True):
    init_app(routes=False)
    node_logs = models.NodeLog.find()
    log_count = node_logs.count()
    errored_logs = []
    for count, log in enumerate(node_logs):
        with TokuTransaction():
            log.original_node = get_original_node(log)
            log.node = get_original_node(log)
            if not dry:
                try:
                    log.save()
                except KeyError as error:
                    logger.error('Could not migrate log due to error')
                    logger.exception(error)
                    errored_logs.append(log)
                else:
                    logger.info('{}/{} Log {} "original_node and node" added'.format(count, log_count, log._id))

    if errored_logs:
        logger.error('{} errored'.format(len(errored_logs)))
        logger.error('\n'.join([each._id for each in errored_logs]))

    for count, log in enumerate(node_logs): # for every log in node_logs
        with TokuTransaction():
            errored_clones = []
            for node in log._backrefs['logged']['node']['logs']:
                if node != log.original_node._id:
                    clone = log.clone_node_log(node)
                    clone.original_node = get_original_node(log)
                    try:
                        clone.save()
                        logger.info('Log {} cloned for node {}. New log is {}'.format(log._id, node, clone._id))
                    except KeyError as error:
                        logger.error('Could not copy node log due to error')
                        logger.exception(error)
                        errored_clones.append(log, clone)


if __name__ == '__main__':

    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry_run)
