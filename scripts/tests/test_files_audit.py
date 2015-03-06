# -*- coding: utf-8 -*-
import os

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from website.addons.osfstorage.tests.factories import FileVersionFactory
from scripts.osfstorage import settings as storage_settings
from scripts.osfstorage.files_audit import ensure_parity, ensure_glacier, download_from_cloudfiles


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
    @mock.patch('scripts.osfstorage.files_audit.storage_utils.create_parity_files')
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.container_parity')
    def test_ensure_parity(self, mock_container, mock_download, mock_create_parity, mock_remove):
        mock_container.list_all.return_value = []
        mock_create_parity.return_value = ['hi'] * 8
        version = FileVersionFactory()
        ensure_parity(version, dry_run=False)
        assert_equal(len(mock_container.create.call_args_list), 8)

    @mock.patch('scripts.osfstorage.files_audit.storage_utils.create_parity_files')
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.container_parity')
    def test_ensure_parity_exists(self, mock_container, mock_download, mock_create_parity):
        mock_container.list_all.side_effect = [['hi'], ['hi'] * 4]
        version = FileVersionFactory()
        ensure_parity(version, dry_run=False)
        assert_false(mock_download.called)
        assert_false(mock_container.create.called)
