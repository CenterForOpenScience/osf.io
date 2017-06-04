# -*- coding: utf-8 -*-
"""Restore a deleted StoredFileNode. If the file was reuploaded, renames the file
to <filename> (restored).<ext>. For example, README.rst would be renamed to README (restored).rst.

    python -m scripts.restore_file 123ab --dry
    python -m scripts.restore_file 123ab

"""
import sys
import os
import logging

from modularodm.exceptions import KeyExistsException

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import Guid
from website.files.models.base import TrashedFileNode
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def rename_file(file_node):
    name, ext = os.path.splitext(file_node.name)
    new_name = ''.join([name, ' (restored)', ext])
    logger.info('Renaming {} to {}'.format(file_node.name, new_name))
    file_node.name = new_name

    name, ext = os.path.splitext(file_node.materialized_path)
    new_mpath = ''.join([name, ' (restored)', ext])
    logger.info('Changing materialized_path from {} to {}'.format(file_node.materialized_path, new_mpath))
    file_node.materialized_path = new_mpath
    file_node.save()


def restore_file(guid):
    guid_obj = Guid.load(guid)
    trashed_file_node = guid_obj.referent
    assert isinstance(trashed_file_node, TrashedFileNode), 'Guid does not point to a trashedfilenode'
    logger.info('Loaded trashedfilenode {}'.format(trashed_file_node._id))
    try:
        logger.info('Calling restore()')
        trashed_file_node.restore()
    except KeyExistsException:  # File with same name exists; user most likely re-uploaded file
        logger.warn('File with name {} exists. Renaming...'.format(trashed_file_node.name))
        rename_file(trashed_file_node)
        logger.info('Calling restore()')
        trashed_file_node.restore()
    return True


def main():
    init_app(routes=False)
    guid = sys.argv[1]
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        restore_file(guid)
        if dry:
            raise RuntimeError('Dry run - rolling back transaction')

if __name__ == "__main__":
    main()
