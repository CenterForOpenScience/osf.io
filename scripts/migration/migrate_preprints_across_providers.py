import argparse
import json
import logging

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app

logger = logging.getLogger(__name__)


def validate_target(target):
    assert database.preprintservice.find({'_id': target.get('preprint_id')}).count(), 'Unable to find PreprintService with _id {}'.format(target.get('preprint_id'))
    assert database.preprintprovider.find({'_id': target.get('provider_id')}).count(), 'Unable to find PreprintProvider with _id {}'.format(target.get('provider_id'))

def migrate(targets):
    for target in targets:
        validate_target(target)
        logger.info('Updating PreprintService {preprint_id} provider to {provider_id}'.format(**target))
        database.preprintservice.find_and_modify(
            {'_id': target['preprint_id']},
            {'$set': {'provider': target['provider_id']}}
        )

def main():
    parser = argparse.ArgumentParser(
        description='Changes the provider of specified PreprintService objects'
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Run migration and roll back changes to db',
    )
    parser.add_argument(
        '--targets',
        action='store',
        dest='targets',
        help='List of targets, of form {"data": [{"preprint_id": "<_id>", "provider_id": "<_id>"}, ...]}',
    )
    pargs = parser.parse_args()
    if not pargs.dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(targets=json.loads(pargs.targets)['data'])
        if pargs.dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
