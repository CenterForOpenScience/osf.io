#!/usr/bin/env python
# encoding: utf-8

"""Verify that all OSF Storage files have Glacier backups and parity files,
creating any missing backups.

TODO: Add check against Glacier inventory
Note: Must have par2 installed to run
"""

import os
import logging

import pyrax
from boto.glacier.layer2 import Layer2

from website.app import init_app
from website.addons.osfstorage import model

from scripts.osfstorage import utils as script_utils
from scripts.osfstorage import settings as storage_settings


container_primary = None
container_parity = None
vault = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def download_from_cloudfiles(version):
    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    if os.path.exists(path):
        return
    obj = container_primary.get_object(version.location['object'])
    obj.download(storage_settings.AUDIT_TEMP_PATH)
    return path


def delete_temp_file(version):
    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    try:
        os.remove(path)
    except OSError:
        pass


def ensure_glacier(version, dry_run):
    if version.metadata.get('archive'):
        return
    logger.info('Glacier archive for version {0} not found'.format(version._id))
    if dry_run:
        return
    download_from_cloudfiles(version)
    file_path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    glacier_id = vault.upload_archive(file_path, description=version.location['object'])
    version.metadata['archive'] = glacier_id
    version.save()


def check_parity_files(version):
    index = list(container_parity.list_all(prefix='{0}.par2'.format(version.location['object'])))
    vols = list(container_parity.list_all(prefix='{0}.vol'.format(version.location['object'])))
    return len(index) == 1 and len(vols) >= 1


def ensure_parity(version, dry_run):
    if check_parity_files(version):
        return
    logger.info('Parity files for version {0} not found'.format(version._id))
    if dry_run:
        return
    file_path = download_from_cloudfiles(version)
    parity_paths = script_utils.create_parity_files(file_path)
    for parity_path in parity_paths:
        container_parity.create(parity_path)
        os.remove(parity_path)
    if not check_parity_files(version):
        logger.error('Parity files for version {0} not found after update'.format(version._id))


def ensure_backups(version, dry_run):
    if version.size == 0:
        logger.info('Skipping empty version {0}'.format(version._id))
        return
    ensure_glacier(version, dry_run)
    ensure_parity(version, dry_run)
    delete_temp_file(version)


def get_targets():
    return model.OsfStorageFileVersion.find()


def main(dry_run):
    for version in get_targets():
        ensure_backups(version, dry_run)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv

    # Set up storage backends
    init_app()

    # Authenticate to Rackspace
    pyrax.settings.set('identity_type', 'rackspace')
    pyrax.set_credentials(
        storage_settings.USERNAME,
        storage_settings.API_KEY,
        region=storage_settings.REGION
    )
    container_primary = pyrax.cloudfiles.get_container(storage_settings.PRIMARY_CONTAINER_NAME)
    container_parity = pyrax.cloudfiles.get_container(storage_settings.PARITY_CONTAINER_NAME)

    # Connect to AWS
    layer2 = Layer2(
        aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
        aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
    )
    vault = layer2.get_vault(storage_settings.GLACIER_VAULT)

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)


import mock

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from website.addons.osfstorage.tests.factories import FileVersionFactory


class TestFilesAudit(OsfTestCase):

    @mock.patch('os.path.exists')
    @mock.patch('scripts.osfstorage.files_audit.container_primary')
    def test_download(self, mock_container, mock_exists):
        mock_object = mock.Mock()
        mock_container.get_object.return_value = mock_object
        mock_exists.return_value = False
        version = FileVersionFactory()
        download_from_cloudfiles(version)
        mock_container.get_object.assert_called_with(version.location['object'])
        mock_object.download.assert_called_with(storage_settings.AUDIT_TEMP_PATH)

    @mock.patch('os.path.exists')
    @mock.patch('scripts.osfstorage.files_audit.container_primary')
    def test_download_exists(self, mock_container, mock_exists):
        mock_exists.return_value = True
        assert_false(mock_container.get_object.called)

    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.vault')
    def test_ensure_glacier(self, mock_vault, mock_download):
        glacier_id = 'iamarchived'
        mock_vault.upload_archive.return_value = glacier_id
        version = FileVersionFactory()
        ensure_glacier(version, dry_run=False)
        key = version.location['object']
        mock_vault.upload_archive.assert_called_with(os.path.join(storage_settings.AUDIT_TEMP_PATH, key), description=key)
        version.reload()
        assert_equal(version.metadata['archive'], glacier_id)

    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.vault')
    def test_ensure_glacier_exists(self, mock_vault, mock_download):
        version = FileVersionFactory()
        version.metadata['archive'] = 'foo'
        version.save()
        ensure_glacier(version, dry_run=False)
        assert_false(mock_vault.upload_archive.called)

    @mock.patch('os.remove')
    @mock.patch('scripts.osfstorage.files_audit.script_utils.create_parity_files')
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.container_parity')
    def test_ensure_parity(self, mock_container, mock_download, mock_create_parity, mock_remove):
        mock_container.list_all.return_value = []
        mock_create_parity.return_value = ['hi'] * 8
        version = FileVersionFactory()
        ensure_parity(version, dry_run=False)
        assert_equal(len(mock_container.create.call_args_list), 8)

    @mock.patch('scripts.osfstorage.files_audit.script_utils.create_parity_files')
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.container_parity')
    def test_ensure_parity_exists(self, mock_container, mock_download, mock_create_parity):
        mock_container.list_all.side_effect = [['hi'], ['hi'] * 4]
        version = FileVersionFactory()
        ensure_parity(version, dry_run=False)
        assert_false(mock_download.called)
        assert_false(mock_container.create.called)
