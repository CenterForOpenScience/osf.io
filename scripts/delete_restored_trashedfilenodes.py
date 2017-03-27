# -*- coding: utf-8 -*-
"""Restore a deleted StoredFileNode. If the file was reuploaded, renames the file
to <filename> (restored).<ext>. For example, README.rst would be renamed to README (restored).rst.

    python -m scripts.restore_file 123ab --dry
    python -m scripts.restore_file 123ab

"""
import sys
import logging

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.files.models.base import TrashedFileNode, StoredFileNode
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        stored = StoredFileNode.find().get_keys()
        trashed = TrashedFileNode.find().get_keys()

        stored_set = set(stored)
        trashed_set = set(trashed)

        intersection = trashed_set & stored_set

        print('There are {} restored trashed file nodes'.format(len(intersection)))

        for trash_id in intersection:
            TrashedFileNode.remove_one(trash_id)
            print('Removed TrashedFileNode {}'.format(trash_id))

        if dry:
            raise RuntimeError('Dry run - rolling back transaction')

if __name__ == "__main__":
    main()
