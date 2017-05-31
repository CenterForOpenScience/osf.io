"""Fixes cases where multiple node/user settings for a given addon are attached to a single node/user.
This ensures that node and user settings are unique on owner and provider.
"""
import sys
import logging

import bson

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def is_active(collection_name, document):
    """Return whether the given node settings document is active, e.g. has an external
    account or is configured.
    """
    if collection_name == 'addonfigsharenodesettings':
        return any([
            document['figshare_type'],
            document['figshare_id'],
            document['figshare_title'],
        ])
    elif collection_name == 'googledrivenodesettings':
        return any([
            document['folder_path'],
            document['user_settings'],
            document['folder_id'],
        ])
    elif collection_name == 'forwardnodesettings':
        return document.get('url', False)
    else:
        return bool(document['external_account'])


def fix_duplicate_addon_node_settings():
    COLLECTIONS = [
        'forwardnodesettings',
        'addondataversenodesettings',
        'addonfigsharenodesettings',
        # 'addongithubnodesettings',  # old, unused
        'addonowncloudnodesettings',
        # 'addons3nodesettings',  # old, unused
        'boxnodesettings',
        'figsharenodesettings',
        'dropboxnodesettings',
        'githubnodesettings',
        'googledrivenodesettings',
        'mendeleynodesettings',
        'osfstoragenodesettings',
        's3nodesettings',
        'zoteronodesettings',
        'addonwikinodesettings',
    ]

    for collection in COLLECTIONS:
        targets = database[collection].aggregate([
            {
                "$group": {
                    "_id": "$owner",
                    "ids": {"$addToSet": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            },
            {
                "$sort": {
                    "count": -1
                }
            }
        ]).get('result')

        for group in targets:
            if not group['_id']:
                for _id in group['ids']:
                    if _id:
                        logger.info('No owner for {} {}. Removing.'.format(collection, _id))
                        database[collection].remove(_id)
                    else:
                        logger.info('_id was None: {}'.format(group))
            else:
                logger.info(
                    '{} {} found for node {}'.format(
                        len(group['ids']), collection, group['_id']
                    )
                )
                active_ns = []
                for _id in group['ids']:
                    node_settings = database[collection].find_one(_id)
                    if is_active(collection, node_settings):
                        active_ns.append(_id)
                if not active_ns:
                    logger.info('No configured {} on node {}. Keeping the first record...'.format(
                        collection, group['_id']
                    ))
                    good = group['ids'].pop()
                    for bad in group['ids']:
                        if bad:
                            logger.info('Removing {} from {}'.format(bad, collection))
                            database[collection].remove(bad)
                        else:
                            logger.info('_id was None: {}'.format(group))
                elif len(active_ns) == 1:
                    logger.info('Found one active {} for node {}: {}'.format(
                        collection, group['_id'], active_ns[0]
                    ))
                    for _id in group['ids']:
                        if not _id:
                            logger.info('_id was None: {}'.format(group))
                            continue
                        if _id not in active_ns:
                            logger.info('Removing {} from {}'.format(_id, collection))
                            database[collection].remove(_id)
                else:
                    raise RuntimeError(
                        'Expected 0 or 1 active node settings'
                    )


def fix_duplicate_addon_user_settings():
    COLLECTIONS = [
        'addondataverseusersettings',
        'addonfigshareusersettings',
        # 'addongithubusersettings',  # old, unused
        'addonowncloudusersettings',
        # 'addons3usersettings',  # old, unused
        'boxusersettings',
        'dropboxusersettings',
        'githubusersettings',
        'googledriveusersettings',
        'mendeleyusersettings',
        'osfstorageusersettings',
        's3usersettings',
        'zoterousersettings',
        'addonwikiusersettings'
    ]
    for collection in COLLECTIONS:
        targets = database[collection].aggregate([
            {
                "$group": {
                    "_id": "$owner",
                    "ids": {"$addToSet": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            },
            {
                "$sort": {
                    "count": -1
                }
            }
        ]).get('result')
        for group in targets:
            logger.info(
                '{} {} found for user {}'.format(
                    len(group['ids']), collection, group['_id']
                )
            )
            oauth_grants = {}
            update_grants = False
            bad = []
            good = []
            newest = None
            # Merge existing oauth_grants
            for _id in group['ids']:
                instance = database[collection].find_one(_id)
                if 'oauth_grants' in instance:
                    oauth_grants.update(instance['oauth_grants'])
                    update_grants = True
                if instance['deleted']:
                    bad.append(instance)
                else:
                    good.append(instance)
            for us in good:
                if not newest or bson.ObjectId(us['_id']).generation_time > bson.ObjectId(newest['_id']).generation_time:
                    newest = us
            # remove the keeper
            logger.info('Keeping {} {}'.format(collection, newest['_id']))
            good.pop(good.index(newest))
            if update_grants:
                logger.info('Updating {} oauth_grants to {}'.format(newest['_id'], oauth_grants))
                database[collection].update({'_id': newest['_id']}, {"$set": {'oauth_grants': oauth_grants}})
            # Remove duplicate
            for worst in good + bad:
                logger.info('Removing {} from {}'.format(worst['_id'], collection))
                database[collection].remove(worst['_id'])

def main():
    fix_duplicate_addon_node_settings()
    fix_duplicate_addon_user_settings()
    print('Done.')


if __name__ == '__main__':
    # Enable console output
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(name)s]  %(levelname)s: %(message)s',
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')
