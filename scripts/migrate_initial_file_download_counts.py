import logging
import sys

import datetime
from website.app import setup_django
setup_django()
from django.db import transaction

from admin.metrics.views import FileDownloadCounts
from framework.analytics import get_basic_counters
from osf.models.files import File, TrashedFile
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)


def get_number_downloads_unique_and_total():
    number_downloads_unique = 0
    number_downloads_total = 0

    for file_node in File.objects.all():
        page = ':'.join(['download', file_node.node._id, file_node._id])
        unique, total = get_basic_counters(page)
        number_downloads_unique += unique or 0
        number_downloads_total += total or 0

    for file_node in TrashedFile.objects.all():
        page = ':'.join(['download', file_node.node._id, file_node._id])
        unique, total = get_basic_counters(page)
        number_downloads_unique += unique or 0
        number_downloads_total += total or 0

    return number_downloads_unique, number_downloads_total


def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        scripts_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        number_downloads_unique, number_downloads_total = get_number_downloads_unique_and_total()
        FileDownloadCounts.set_download_counts(
            number_downloads_total=number_downloads_total,
            number_downloads_unique=number_downloads_unique,
            update_date=datetime.datetime.now()
        )
        logger.info('Download counts migrated. Total download number is {}. Unique download number is {}.'.format(
            number_downloads_total, number_downloads_unique)
        )


if __name__ == '__main__':
    init_app(routes=False)
    main()
