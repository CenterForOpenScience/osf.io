import logging

from website.app import setup_django
setup_django()

import argparse
from datetime import timedelta
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials

from framework.sentry import log_exception
from osf.models.files import TrashedFile
from website.settings import GCS_CREDS, PURGE_DELTA

logger = logging.getLogger(__name__)

def purge_trash(n):
    qs = TrashedFile.objects.filter(purged__isnull=True, deleted__lt=timezone.now()-PURGE_DELTA, provider='osfstorage')
    creds = Credentials.from_service_account_file(GCS_CREDS)
    client = Client(credentials=creds)
    total_bytes = 0
    for tf in qs[:n]:
        try:
            total_bytes += tf._purge(client=client)
        except Exception as e:
            log_exception()
            logger.error(f'Encountered Error handling {tf.id}')
    return total_bytes

def main():
    parser = argparse.ArgumentParser(
        description=f'Purges TrashedFiles deleted more than {PURGE_DELTA} days ago.'
    )
    parser.add_argument(
        '-n',
        '--num',
        type=int,
        dest='num_records',
        default=50000,
        help='Batch size',
    )
    pargs = parser.parse_args()
    total = purge_trash(pargs.num_records)
    readable_total = filesizeformat(total)
    logger.info(f'Freed {readable_total}.')

if __name__ == '__main__':
    main()
