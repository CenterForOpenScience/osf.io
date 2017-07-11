import logging
import sys
import time

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from addons.s3.utils import get_bucket_location_or_error
from addons.s3.settings import BUCKET_LOCATIONS
from addons.s3.model import S3NodeSettings
from scripts import utils as script_utils


logger = logging.getLogger(__name__)


def migrate(dry_run=False):
    bucket_name_location_map = {}
    sns_collection = database['s3nodesettings']
    logger.info('Migrating all {} S3NodeSettings documents: {}'.format(
        sns_collection.count(), [s['_id'] for s in sns_collection.find()]
    ))
    for document in sns_collection.find():
        sns_collection.find_and_modify(
            {'_id': document['_id']},
            {
                '$set': {'folder_id': document['bucket'], 'folder_name': document['bucket']},
                '$unset': {'bucket': ''}
            }
        )

    allowance = 2
    last_call = time.time()
    for node_settings in S3NodeSettings.find(Q('folder_id', 'ne', None)):
        if node_settings.folder_id in bucket_name_location_map:
            # See if this bucket is cached
            node_settings.folder_name = '{} ({})'.format(
                node_settings.folder_id,
                bucket_name_location_map[node_settings.folder_id]
            )
        else:
            # Attempt to determine bucket location, default to just bucket name.
            node_settings.folder_name = node_settings.folder_id

            if allowance < 1:
                try:
                    time.sleep(1 - (time.time() - last_call))
                except (ValueError, IOError):
                    pass  # ValueError/IOError indicates a negative sleep time
                allowance = 2

            allowance -= 1
            last_call = time.time()

            bucket_location = None
            try:
                bucket_location = get_bucket_location_or_error(
                    node_settings.external_account.oauth_key,
                    node_settings.external_account.oauth_secret,
                    node_settings.folder_id
                )
            except InvalidAuthError:
                logger.info('Found S3NodeSettings {} with invalid credentials.'.format(node_settings._id))
            except InvalidFolderError:
                logger.info('Found S3NodeSettings {} with invalid bucket linked.'.format(node_settings._id))
            except Exception as e:
                logger.info('Found S3NodeSettings {} throwing unknown error. Likely configured improperly; with a bucket but no credentials'.format(node_settings._id))
                logger.exception(e)
            else:
                try:
                    bucket_location = BUCKET_LOCATIONS[bucket_location]
                except KeyError:
                    # Unlisted location, S3 may have added it recently.
                    # Default to the key. When hit, add mapping to settings
                    logger.info('Found unknown location key: {}'.format(bucket_location))

                node_settings.folder_name = '{} ({})'.format(node_settings.folder_id, bucket_location)
                bucket_name_location_map[node_settings.folder_id] = bucket_location

            if not bucket_location:
                node_settings.folder_name = node_settings.folder_id

        node_settings.save()

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == '__main__':
    main()
