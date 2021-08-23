import logging

from website.app import setup_django
setup_django()

import argparse
from django.template.defaultfilters import filesizeformat
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials

from framework.sentry import log_exception
from osf.models.files import TrashedFile
from website.settings import GCS_CREDS

logger = logging.getLogger(__name__)

def unpurge_trash(ids):
    qs = TrashedFile.objects.filter(purged__isnull=False, id__in=ids)
    creds = Credentials.from_service_account_file(GCS_CREDS)
    client = Client(credentials=creds)
    if qs.count() < len(ids):
        logger.warn('Some ids could not be found: {}'.format(list(set(ids) - set(qs.values_list('id', flat=True)))))
    for tf in qs.all():
        logger.info(f'Unpurging {tf.id}')
        try:
            tf.restore(client=client)
        except Exception as e:
            log_exception()
            logger.error(f'Encountered Error handling {tf.id}')

def main():
    parser = argparse.ArgumentParser(
        description=f'Unpurges TrashedFiles by id'
    )
    parser.add_argument(
        'ids',
        metavar='N',
        type=int,
        nargs='+',
        required=True,
        help='IDs of Purged files to restore.',
    )
    pargs = parser.parse_args()
    unpurge_trash(pargs.ids)
    logger.info('Complete.')

if __name__ == '__main__':
    main()
