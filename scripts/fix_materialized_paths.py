"""
Fix any file materialized paths that are missing a beginning "/".
Addresses https://openscience.atlassian.net/browse/OSF-5954 for existing files.
"""
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.files.models import StoredFileNode
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    files = StoredFileNode.find(Q('provider', 'ne', 'osfstorage'))
    update_file_materialized_paths(files)


def update_file_materialized_paths(files):
    for file_obj in files:
        if not file_obj.materialized_path.startswith('/'):
            file_obj.materialized_path = '/' + file_obj.materialized_path
            file_obj.save()
            logger.info('Updated materialized path for file {0} to {1}'.format(file_obj._id, file_obj.materialized_path))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')