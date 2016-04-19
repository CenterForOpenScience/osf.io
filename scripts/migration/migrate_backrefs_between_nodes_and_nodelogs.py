"""
This migration will add original_node and node associated with the log to nodelogs. It will then
clone each nodelog for the remaining nodes in the backref (registrations and forks),
changing the node to the current node.
"""
from bson import ObjectId
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
    cursor = db.nodelog.find({'original_node': None})
    cursor.batch_size(10000)

    count = cursor.count()
    done = 0

    to_insert = []
    for log in cursor:
        try:
            try:
                node = log['__backrefs']['logged']['node']['logs'][0]
                tagged = log['__backrefs']['logged']['node']['logs'][1:]
            except (KeyError, IndexError):
                # If backrefs don't exist fallback to node/project with priority to node
                node = log['params'].get('node') or log['params'].get('project')
                # If project is different from the node we've found clone the logs for it
                if log['params'].get('project', node) != node:
                    tagged = [log['params']['project']]
                else:
                    tagged = []

            assert node is not None, 'Could not find a node for {}'.format(log)

            db.nodelog.update({'_id': log['_id']}, {'$set': {
                'node': node,
                'original_node': log['params'].get('node', node),
            }})
        except Exception as error:
            if log == {'__backrefs': {}, 'params': {}, '_id': log['_id']} or log == {'__backrefs': {'logged': {'node': {'logs': []}}}, 'params': {}, '_id': log['_id']}:
                logger.warning('log {} is empty. Skipping.'.format(log['_id']))
            else:
                logger.error('Could not migrate nodelog {} due to error'.format(log))
                logger.exception(error)
            continue
        finally:
            done += 1

        for other in tagged:
            clone = deepcopy(log)
            clone['_id'] = str(ObjectId())
            clone.pop('__backrefs', None)
            clone['original_node'] = log['params'].get('node', node)
            clone['node'] = other
            to_insert.append(clone)

        if len(to_insert) > 9999:
            count += len(to_insert)
            result = db.nodelog.insert(to_insert)
            to_insert = []
            done += len(result)
            logger.info('{}/{} Logs updated'.format(done, count))

    if len(to_insert) > 0:
        count += len(to_insert)
        result = db.nodelog.insert(to_insert)
        to_insert = []
        done += len(result)
        logger.info('{}/{} Logs updated'.format(done, count))

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
