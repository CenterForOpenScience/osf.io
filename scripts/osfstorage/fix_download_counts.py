from __future__ import unicode_literals
import sys
import logging
from framework.mongo import database
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)

# 2015 Sept 18
CUT_OFF_DATE = (2015, 9, 18)

BACKUP_COLLECTION = '20151009pagecounters'


def get_keys_after(obj, y, m, d):
    keys = []
    for date in obj['date'].keys():
        year, month, day = date.split('/')
        if int(year) >= y and int(month) >= m and int(day) >= d:
            keys.append(date)
    return keys


def do_migration():
    database.pagecounters.rename(BACKUP_COLLECTION)

    for download_count in database[BACKUP_COLLECTION].find():
        if not download_count['_id'].startswith('download'):
            database.pagecounters.insert(download_count)
            continue

        try:
            _, nid, fid, version = download_count['_id'].split(':')
        except ValueError:
            if download_count['_id'].count(':') != 2:
                logging.warning('Found malformed _id {}'.format(download_count['_id']))
            database.pagecounters.insert(download_count)
            continue

        try:
            version = int(version)
        except ValueError:
            logging.warning('Found malformed version in _id {}'.format(download_count['_id']))
            database.pagecounters.insert(download_count)
            continue

        previous_version = database[BACKUP_COLLECTION].find_one({
            '_id': ':'.join(['download', nid, fid, str(version - 1)])
        })

        if previous_version:
            logger.debug('Found previous version for {}'.format(download_count['_id']))
            previous_version_keys = get_keys_after(previous_version, *CUT_OFF_DATE)
        else:
            logger.debug('No previous version found for {}'.format(download_count['_id']))
            previous_version = {
                '_id': ':'.join(['download', nid, fid, str(version - 1)]),
                'unique': 0,
                'total': 0,
                'date': {}
            }
            previous_version_keys = []

        # 2015 Sept 18
        keys = get_keys_after(download_count, *CUT_OFF_DATE)

        if not keys and not previous_version_keys:
            logger.debug('{} not affected, copying'.format(download_count['_id']))
            database.pagecounters.insert(download_count)
            continue

        if version < 1:
            try:
                assert len(keys) == 1 and not previous_version_keys
            except AssertionError:
                logger.error('{} contains a keys on {}, ignoring and copying'.format(download_count['_id'], ', '.join(keys)))
            else:
                logger.warning('{} contains a key on the cut off date, ignoring the key and copying'.format(download_count['_id']))
            database.pagecounters.insert(download_count)
            continue

        for key in previous_version_keys:
            date = previous_version['date'].pop(key)
            previous_version['total'] -= date['total']
            previous_version['unique'] -= date['unique']

        for key in keys:
            date = download_count['date'][key]
            existing = previous_version['date'].setdefault(key, {'total': 0, 'unique': 0})
            existing['total'] += date['total']
            existing['unique'] += date['unique']
            previous_version['total'] += date['total']
            previous_version['unique'] += date['unique']

        assert previous_version['unique'] > -1
        assert previous_version['total'] > -1

        logger.debug('Updating entry {}'.format(previous_version['_id']))
        database.pagecounters.update({'_id': previous_version['_id']}, previous_version, upsert=True)


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
