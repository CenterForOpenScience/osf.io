import sys
import logging
from modularodm import Q

from website.app import init_app
from website.files.models import FileVersion

from scripts import utils as script_utils

from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)


def do_migration():
    logger.info('Starting sha256 recovery migration')
    for version in FileVersion.find(Q('metadata.sha256', 'eq', None)):
        if not version.location:
            continue
        logger.debug('Adding sha {} to version {}'.format(version.location['object'], version._id))
        version.metadata['sha256'] = version.location['object']
        version.save()

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
    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)
    main(dry=dry)
