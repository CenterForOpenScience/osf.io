from __future__ import unicode_literals
import sys
import logging
from datetime import datetime
from framework.mongo import database
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)

# 2015 Sept 18
CUT_OFF_DATE = (2015, 9, 18)

BACKUP_COLLECTION = 'zzz20151009pagecounters'
NEW_COLLECTION = '20151009pagecountersmigrated'


def get_keys_after(obj, y, m, d):
    cut_off = datetime(year=y, month=m, day=d)
    keys = []
    for date in obj['date'].keys():
        year, month, day = date.split('/')
        if datetime(year=int(year), month=int(month), day=int(day)) >= cut_off:
            keys.append(date)
    return keys


def do_migration():
    # database.pagecounters.rename(BACKUP_COLLECTION)

    for current_version in database['pagecounters'].find():
        if not current_version['_id'].startswith('download'):
            database[NEW_COLLECTION].insert(current_version)
            continue

        try:
            _, nid, fid, version = current_version['_id'].split(':')
        except ValueError:
            if current_version['_id'].count(':') != 2:
                logging.warning('Found malformed _id {}'.format(current_version['_id']))
            database[NEW_COLLECTION].insert(current_version)
            continue

        try:
            version = int(version)
        except ValueError:
            logging.warning('Found malformed version in _id {}'.format(current_version['_id']))
            database[NEW_COLLECTION].insert(current_version)
            continue

        next_version = database['pagecounters'].find_one({
            '_id': ':'.join(['download', nid, fid, str(version + 1)])
        })

        if next_version:
            logger.debug('Found next version for {}'.format(current_version['_id']))
            next_version_keys = get_keys_after(next_version, *CUT_OFF_DATE)
        else:
            logger.debug('No next version found for {}'.format(current_version['_id']))
            next_version_keys = []

        # 2015 Sept 18
        current_version_keys = get_keys_after(current_version, *CUT_OFF_DATE)

        if current_version_keys:
            if not database['pagecounters'].find_one({'_id': ':'.join(['download', nid, fid, str(version - 1)])}):
                previous_version = {'_id': ':'.join(['download', nid, fid, str(version - 1)]), 'date': {}, 'total': 0, 'unique': 0}
                for key in current_version_keys:
                    date = current_version['date'][key]
                    previous_version['date'][key] = date
                    previous_version['total'] += date['total']
                    previous_version['unique'] += date['unique']

                database[NEW_COLLECTION].insert(previous_version)

        for key in current_version_keys:
            date = current_version['date'].pop(key)
            current_version['total'] -= date['total']
            current_version['unique'] -= date['unique']

        for key in next_version_keys:
            date = next_version['date'][key]
            assert key not in current_version
            current_version['date'][key] = date
            current_version['total'] += date['total']
            current_version['unique'] += date['unique']

        assert current_version['unique'] > -1
        assert current_version['total'] > -1

        if current_version['total'] == 0 or current_version['unique'] == 0 or not current_version['date']:
            assert not current_version['date']
            assert current_version['total'] == 0
            assert current_version['unique'] == 0
            logger.warning('Skipping {} as it is a null record'.format(current_version['_id']))
            continue

        logger.debug('Updating entry {}'.format(current_version['_id']))
        database[NEW_COLLECTION].insert(current_version)

    database['pagecounters'].rename(BACKUP_COLLECTION)
    database[NEW_COLLECTION].rename('pagecounters')


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Allow setting the log level just by appending the level to the command
    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)
    main(dry=dry)
