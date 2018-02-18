import logging
import sys

from website.app import setup_django
setup_django()

from framework.analytics import get_basic_counters
from osf.models.files import File, TrashedFile
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)


def get_number_downloads_unique_and_total(self):
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


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    init_app(routes=False)
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    get_number_downloads_unique_and_total(dry=dry)