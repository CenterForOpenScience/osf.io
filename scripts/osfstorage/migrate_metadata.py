# -*- coding: utf-8 -*-
"""Script which ensures that every file version's
content_type, size, and date_modified fields are consistent
with the metadata from waterbutler.
"""
from modularodm import Q
import logging
import sys

from website.addons.osfstorage.model import OsfStorageFileVersion
from website.app import init_app

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)

def main():
    for each in OsfStorageFileVersion.find(
        Q('size', 'eq', None) &
        Q('status', 'ne', 'cached') &
        Q('location.object', 'exists', True)
    ):
        logger.info('Updating metadata for OsfStorageFileVersion {}'.format(each._id))
        if 'dry' not in sys.argv:
            each.update_metadata(each.metadata)
            each.save()

if __name__ == '__main__':
    # Set up storage backends
    init_app(set_backends=True, routes=False)
    if 'dry' not in sys.argv:
        scripts_utils.add_file_logger(logger, __file__)
    main()
