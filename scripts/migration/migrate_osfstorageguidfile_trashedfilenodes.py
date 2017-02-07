import logging
import re
import sys

from framework.mongo import database
from website.app import init_app
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def get_targets():
    guids = [
        x['_id']
        for x in database['guid'].find(
            {'referent': 'osfstorageguidfile'},
            {'_id': True}
        )
    ]

    paths = {
        x['path'].strip('/'): x['_id']
        for x in database['osfstorageguidfile'].find({
            '_id': {'$in': guids},
            'path': {'$not': re.compile('.*{{.*')}
        }, {'path': True})
    }
    return paths, database['trashedfilenode'].find({'_id': {'$in': list(paths.keys())}})

def migrate():
    paths, targets = get_targets()
    for trashed in targets:
        logger.info('Migrating {} => {}'.format(paths[trashed['_id']], trashed['_id']))
        database['guid'].update(
            {'_id': paths[trashed['_id']]},
            {'$set': {
                'referent': (trashed['_id'], 'trashedfilenode')
            }}
        )

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate()
        if dry_run:
            raise RuntimeError('Dry Run -- Transaction rolled back')


if __name__ == '__main__':
    main()
