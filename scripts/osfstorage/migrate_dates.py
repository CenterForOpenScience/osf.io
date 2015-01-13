#!/usr/bin/env python
# encoding: utf-8

import logging
import datetime

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website import settings
from website.models import Node
from website.app import init_app
from website.addons.osffiles.model import NodeFile
from website.addons.osfstorage.model import OsfStorageFileRecord

from scripts import utils as script_utils
from scripts.osfstorage.utils import ensure_osf_files


logger = logging.getLogger(__name__)
script_utils.add_file_logger(logger, __file__)
logging.basicConfig(level=logging.INFO)


def migrate_version(idx, node_file, record):
    version = record.versions[idx]
    version.date_modified = node_file.date_modified
    version.save()


def migrate_node(node, dry_run=True):
    node_settings = node.get_addon('osfstorage')
    for path, versions in node.files_versions.iteritems():
        for idx, version in enumerate(versions):
            logger.info('Migrating file {0}, version {1} on node {2}'.format(path, idx, node._id))
            if dry_run:
                continue
            try:
                node_file = NodeFile.load(version)
                record = OsfStorageFileRecord.find_by_path(node_file.path, node_settings)
                migrate_version(idx, node_file, record)
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
    ensure_osf_files(settings)
    init_app(set_backends=True, routes=False)
    main(dry_run=dry_run)


# Hack: Must configure add-ons before importing `OsfTestCase`
ensure_osf_files(settings)

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests.factories import FileVersionFactory


class TestMigrateDates(OsfTestCase):

    def setUp(self):
        super(TestMigrateDates, self).setUp()
        self.path = 'old-pizza'
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')
        self.node_file = NodeFile(path=self.path)
        self.node_file.save()
        self.date = self.node_file.date_modified
        self.project.files_versions['old_pizza'] = [self.node_file._id]
        self.project.save()
        self.version = FileVersionFactory(date_modified=datetime.datetime.now())
        self.record = OsfStorageFileRecord.get_or_create(self.node_file.path, self.node_settings)
        self.record.versions = [self.version]
        self.record.save()

    def test_migrate_dates(self):
        assert_not_equal(self.version.date_modified, self.date)
        main(dry_run=False)
        assert_equal(self.version.date_modified, self.date)
