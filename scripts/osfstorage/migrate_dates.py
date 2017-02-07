#!/usr/bin/env python
# encoding: utf-8
"""Ensure correct creation dates on `OsfStorageFileVersion` records created
before migration to OSF Storage. Note: the user-facing date field is called
"date_created" in OSF Storage and "date_modified" in legacy OSF Files.
"""

import logging

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website import settings
from website.models import Node
from website.app import init_app
from addons.osfstorage.model import OsfStorageFileRecord

from scripts import utils as script_utils
from scripts.osfstorage.utils import ensure_osf_files


logger = logging.getLogger(__name__)


def migrate_version(idx, file_data, record, dry_run=True):
    version = record.versions[idx]
    logger.info('Setting OsfStorageFileVersion {} date_created to {}'.format(version._id, file_data['date_modified']))
    if not dry_run:
        version._fields['date_created'].__set__(version, file_data['date_modified'], safe=True)
        version.save()


def migrate_node(node, dry_run=True):
    node_settings = node.get_addon('osfstorage')
    for path, versions in node.files_versions.iteritems():
        for idx, version in enumerate(versions):
            logger.info('Migrating file {0}, version {1} on node {2}'.format(path, idx, node._id))
            try:
                # Note: Use direct mongo lookup to handle deprecation of `NodeFile`
                # collection
                file_data = database['nodefile'].find_one({'_id': version})
                record = OsfStorageFileRecord.find_by_path(file_data['path'], node_settings)
                migrate_version(idx, file_data, record, dry_run=dry_run)
            except Exception as error:
                logger.error('Could not migrate object {0} on node {1}'.format(version, node._id))
                logger.exception(error)
                break


def get_nodes():
    return Node.find(Q('files_versions', 'ne', None))


def main(dry_run=True):
    nodes = get_nodes()
    logger.info('Migrating files on {0} `Node` records'.format(len(nodes)))
    for node in nodes:
        try:
            with TokuTransaction():
                migrate_node(node, dry_run=dry_run)
        except Exception as error:
            logger.error('Could not migrate node {0}'.format(node._id))
            logger.exception(error)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    ensure_osf_files(settings)
    init_app(set_backends=True, routes=False)
    main(dry_run=dry_run)
