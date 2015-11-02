"""
Saves every file to have new save() logic index those files.
"""
import sys
import logging

from website.app import init_app
from website.search import search
from website.files.models.osfstorage import OsfStorageFile

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    logger.warn('Current files will now be updated to be indexed if necessary')
    if dry_run:
        logger.warn('Dry_run mode')
    for file_ in OsfStorageFile.find():
        logger.info(u'File with _id {0} and name {1} has been saved.'.format(file_._id, file_.name))
        if not dry_run:
            search.update_file(file_)

if __name__ == '__main__':
    main()
