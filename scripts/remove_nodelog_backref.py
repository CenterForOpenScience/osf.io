# -*- coding: utf-8 -*-
"""
NOTE: The following scripts need to have run first:

- python -m scripts.fix_forked_logs
- python -m scripts.migrate_registration_logs
"""
from __future__ import division
import json
from bson import ObjectId
import sys
from copy import deepcopy

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import NodeLog
from scripts import utils as script_utils

import logging
logger = logging.getLogger(__name__)

BACKUP_COLLECTION = 'unmigratedlogs'

def copy_log(log, node_id):
    clone = deepcopy(log)
    clone['_id'] = str(ObjectId())
    clone.pop('__backrefs', None)
    clone['original_node'] = get_log_subject(log)
    clone['node'] = node_id.lower()
    return clone

# The remaining, unmigrated logs are orphaned (missing forward and back refs)
# We put them in a separate collection for now
def move_to_backup_collection(log_id):
    log = db.nodelog.find_one({'_id': log_id})
    assert log
    db[BACKUP_COLLECTION].insert(log)
    db.nodelog.remove({'_id': log_id}, just_one=True)


def get_log_subject(log):
    # node_removed logs get stored on a node's parent, which will get handled
    # when we go through a log's backrefs
    if log['action'] == NodeLog.NODE_REMOVED:
        return None
    # node_forked logs get stored on forks, and the fork's ID is in params.registration
    if log['action'] == NodeLog.NODE_FORKED:
        reg = log['params'].get('registration')
        if reg:
            return reg.lower()
        else:  # There is 1 orphaned log for which params.registration is None
            return None
    return (log['params'].get('node') or log['params']['project']).lower()

def migrate_log(log, node_id):
    should_copy = False
    subject = get_log_subject(log)
    if subject != node_id.lower():
        should_copy = True
    else:
        db.nodelog.update({'_id': log['_id']}, {'$set': {
            'node': node_id.lower(),
            'original_node': log['params'].get('node', node_id).lower(),
        }})

    return should_copy


def bulk_insert(logs, remaining):
    result = db.nodelog.insert(logs)
    for each in logs:
        remaining.remove(each['_id'])
    return result


def migrate(dry=True):

    cursor = db.node.find({},
                          {'_id': True, 'logs': True, 'is_registration': True, 'is_fork': True})
    cursor = cursor.batch_size(10000)

    count = db.nodelog.count()

    remaining_log_ids = set([each['_id'] for each in db.nodelog.find({}, {'_id': 1})])

    done = 0
    to_insert = []

    for node in cursor:
        logs = db.nodelog.find({'_id': {'$in': node['logs']}})

        for log in logs:
            should_copy = migrate_log(log=log, node_id=node['_id'])
            if should_copy:
                clone = copy_log(log=log, node_id=node['_id'])
                remaining_log_ids.add(clone['_id'])
                to_insert.append(clone)
            else:
                remaining_log_ids.remove(log['_id'])
                done += 1

            if len(to_insert) > 9999:
                count += len(to_insert)
                result = bulk_insert(to_insert, remaining=remaining_log_ids)
                to_insert = []
                done += len(result)
                logger.info('{}/{} Logs updated ({:.2f}%)'.format(done, count, done / count * 100))

    if len(to_insert) > 0:
        count += len(to_insert)
        result = bulk_insert(to_insert, remaining=remaining_log_ids)
        to_insert = []
        done += len(result)
        logger.info('{}/{} Logs updated ({:.2f}%)'.format(done, count, done / count * 100))

    backref_logs = []
    no_backref = []
    for log_id in list(remaining_log_ids):
        backref_logs.append(log_id)
        log = db.nodelog.find_one({'_id': log_id})
        try:
            node_ids = [e.lower() for e in log['__backrefs']['logged']['node']['logs']]
        except KeyError:
            node_ids = []

        if not node_ids and not log.get('was_connected_to'):
            logger.warn('Null or empty backref for log {}'.format(log_id))
            no_backref.append(log_id)
            continue
        log_subject = get_log_subject(log)
        if log_subject and log_subject not in node_ids:
            logger.warn('Incomplete backref for log {}: does not contain {}'.format(log['_id'], log_subject))
            node_ids.append(log_subject)

        for node_id in node_ids:
            if db.node.find_one({'_id': node_id, 'logs': log['_id']}):
                continue
            should_copy = migrate_log(log=log, node_id=node_id)
            if should_copy:
                clone = copy_log(log=log, node_id=node_id)
                remaining_log_ids.add(clone['_id'])  # XX
                to_insert.append(clone)
            else:
                remaining_log_ids.remove(log['_id'])  # XX
                done += 1

            if len(to_insert) > 9999:
                count += len(to_insert)
                result = bulk_insert(to_insert, remaining=remaining_log_ids)
                to_insert = []
                done += len(result)
                logger.info('{}/{} Logs updated ({:.2f}%)'.format(done, count, done / count * 100))

    if len(to_insert) > 0:
        count += len(to_insert)
        result = bulk_insert(to_insert, remaining=remaining_log_ids)
        to_insert = []
        done += len(result)
        logger.info('{}/{} Logs updated ({:.2f}%)'.format(done, count, done / count * 100))

    # Logs that have was_connected_to should not be migrated, because they
    # were removed from nodes and therefore are expected to have neither
    # forwards nor backwards refs
    expected_unmigrated = set(
        [
            each['_id'] for each in
            db.nodelog.find(
                {'$and': [
                    {'_id': {'$in': list(remaining_log_ids)}},
                    {'was_connected_to': {'$ne': []}},
                    {'was_connected_to': {'$exists': True}},
                ]},
                {'_id': True}
            )
        ]
    )

    unexpected_unmigrated = remaining_log_ids - expected_unmigrated

    for log_id in remaining_log_ids:
        move_to_backup_collection(log_id)

    if unexpected_unmigrated:
        logger.warn('Unexpected unmigrated logs: {}'.format(len(remaining_log_ids)))
        logger.warn(len(remaining_log_ids))

        with open('bads.json', 'w') as fp:  # XX
            json.dump(list(unexpected_unmigrated), fp)  # XX

    logger.info('Updated orphans:')
    logger.info(len(backref_logs))

    if no_backref:
        logger.warn('Skipped logs with no backref: {}'.format(len(no_backref)))

    if dry:
        raise RuntimeError('Dry run -- transaction rolled back')


def main():
    init_app(routes=False)
    dry_run = '--dry' in sys.argv
    if dry_run:
        logger.warn('Running a dry run')
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate(dry=dry_run)

if __name__ == '__main__':
    main()
