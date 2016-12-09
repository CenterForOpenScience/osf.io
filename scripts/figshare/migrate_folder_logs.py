import sys
import logging

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app

logger = logging.getLogger(__name__)


def validate_migration(expected_count):
    logger.info('Validating migration...')
    
    updated_logs = database['nodelog'].find({'action': 'figshare_folder_selected'})
    actual_count = updated_logs.count()
    for log in updated_logs:
        assert log['params']['folder_name'] == log['params']['figshare']['title']
        assert log['params']['folder'] == log['params']['figshare']['type']
        assert log['params']['folder_id'] == log['params']['figshare']['id']

    assert actual_count == expected_count
    logger.info('Done.')


def do_migration(records, dry=False):
    count = records.count()

    for log in records:
        logger.info(
            'Migrating log - {}, '.format(log['_id'])
        )

        params = log['params']
        params.update({
            'folder_name': log['params']['figshare']['title'],
            'folder': log['params']['figshare']['type'],
            'folder_id': log['params']['figshare']['id']
        })
        database['nodelog'].find_and_modify(
            {'_id': log['_id']},
            {
                '$set': {
                    'params': params,
                    'action': 'figshare_folder_selected'
                }
            }
        )

    validate_migration(count)

    logger.info('{}Migrated {} logs'.format('[dry]'if dry else '', count))


def get_targets():
    return database['nodelog'].find({'action': 'figshare_content_linked'})


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        do_migration(get_targets(), dry)
        if dry:
            raise RuntimeError('Dry run, transaction rolled back')


if __name__ == '__main__':
    main()
