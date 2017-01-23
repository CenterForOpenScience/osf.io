#!/usr/bin/env python
# encoding: utf-8
"""Migrate files to correct container.
Note: Must use Rackspace credentials with access to both test and production
containers.
Note: Must have pyrax installed to run.

Run dry run: python -m scripts.migrate_cloudfiles_container dry
Run migration: python -m scripts.migrate_cloudfiles_container

Log:
    Run by sloria, jmcarp, and icereval on 2015-02-10 at 1:15 PM. 822 file version records
    were copied and migrated. A migration log was saved to the migration-logs directory.
"""
import sys
import logging

import pyrax
from modularodm import Q

from website.app import init_app
from addons.osfstorage import model

from scripts import utils as script_utils
from scripts.osfstorage import settings as storage_settings


TEST_CONTAINER_NAME = 'osf_uploads_test'
PROD_CONTAINER_NAME = 'osf_storage_prod'

test_container = None
prod_container = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def migrate_version(version):
    if version.location['container'] != TEST_CONTAINER_NAME:
        raise ValueError('Version is already in correct container')
    key = test_container.get_object(version.location['object'])
    key.copy(prod_container)
    logger.info('Setting container of OsfStorageFileVersion {0} to {1}'.format(
        version._id,
        PROD_CONTAINER_NAME)
    )
    version.location['container'] = PROD_CONTAINER_NAME
    version.save()


def get_targets():
    query = Q('location.container', 'eq', TEST_CONTAINER_NAME)
    return model.OsfStorageFileVersion.find(query)


def main(dry_run):
    versions = get_targets()
    for version in versions:
        logger.info('Migrating OsfStorageFileVersion {0}'.format(version._id))
        if not dry_run:
            migrate_version(version)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    # Authenticate to Rackspace
    pyrax.settings.set('identity_type', 'rackspace')
    pyrax.set_credentials(
        storage_settings.USERNAME,
        storage_settings.API_KEY,
        region=storage_settings.REGION
    )

    # Look up containers
    test_container = pyrax.cloudfiles.get_container(TEST_CONTAINER_NAME)
    prod_container = pyrax.cloudfiles.get_container(PROD_CONTAINER_NAME)

    main(dry_run=dry_run)


import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from addons.osfstorage.tests.factories import FileVersionFactory


class TestMigrateContainer(OsfTestCase):

    def tearDown(self):
        super(TestMigrateContainer, self).tearDown()
        model.OsfStorageFileVersion.remove()

    def test_get_targets(self):
        versions = [FileVersionFactory() for _ in range(5)]
        versions[0].location['container'] = TEST_CONTAINER_NAME
        versions[0].save()
        targets = get_targets()
        assert_equal(len(targets), 1)
        assert_equal(targets[0], versions[0])

    @mock.patch('scripts.migrate_cloudfiles_container.prod_container')
    @mock.patch('scripts.migrate_cloudfiles_container.test_container')
    def test_migrate_version(self, mock_test_container, mock_prod_container):
        mock_test_object = mock.Mock()
        mock_test_container.get_object.return_value = mock_test_object
        version = FileVersionFactory()
        version.location['container'] = TEST_CONTAINER_NAME
        version.save()
        migrate_version(version)
        mock_test_container.get_object.assert_called_with(version.location['object'])
        mock_test_object.copy.assert_called_with(mock_prod_container)
        version.reload()
        assert_equal(version.location['container'], PROD_CONTAINER_NAME)
        assert_equal(len(get_targets()), 0)

    def test_dry_run(self):
        versions = [FileVersionFactory() for _ in range(5)]
        versions[0].location['container'] = TEST_CONTAINER_NAME
        versions[0].save()
        main(dry_run=True)
        assert_equal(len(get_targets()), 1)
