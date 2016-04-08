"""
This migration will add original_node and node associated with the log to nodelogs. It will then
clone each nodelog for the remaining nodes in the backref (registrations and forks),
changing the node to the current node.
"""
from copy import deepcopy
import logging
import sys

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def migrate(dry=True):
    init_app(routes=False)
    node_logs = db.nodelog.find({'original_node': None})
    total_log_count = node_logs.count()
    count = 0

    for log in node_logs:
        count += 1
        try:
            # Step 1: migrate original nodelog - updates existing
            db.nodelog.update(
                {'_id': log['_id']},
                {'$set': {
                    'original_node': log['params']['node'],
                    'node': log['__backrefs']['logged']['node']['logs'][0]
                    }
                },
                upsert=True
            )
            logger.info('{}/{} Log {} updated'.format(count, total_log_count, log['_id']))
        except KeyError as error:
            logger.error('Could not migrate nodelog due to error -- likely a lack of __backrefs')
            logger.exception(error)
        else:
            # Step 2: migrate any backreffed logs - creates new
            for node in log['__backrefs']['logged']['node']['logs'][1:]:
                clone = deepcopy(log)
                clone.pop('_id')
                clone.pop('__backrefs')
                clone['original_node'] = log['params']['node']
                clone['node'] = node
                try:
                    db.nodelog.save(clone)
                    logger.info('{}/{} New log added: {}'.format(count, total_log_count, clone['_id']))
                except KeyError as error:
                    logger.error('Could not create new nodelog due to error')
                    logger.exception(error)
                    pass

    if dry:
        raise RuntimeError('Dry run -- transaction rolled back')

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate(dry=dry_run)

if __name__ == '__main__':
    main()
