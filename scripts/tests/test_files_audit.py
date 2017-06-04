# -*- coding: utf-8 -*-
import os
import shutil

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from website.addons.osfstorage.tests.factories import FileVersionFactory
from scripts.osfstorage import settings as storage_settings
from scripts.osfstorage import files_audit
from scripts.osfstorage.files_audit import ensure_parity, ensure_glacier, download_from_cloudfiles


class TestFilesAudit(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        """Store audit temp files in temp directory.
        """
        super(TestFilesAudit, cls).setUpClass()
        cls._old_audit_temp_path = storage_settings.AUDIT_TEMP_PATH
        cls._audit_temp_path = os.path.join('/tmp', 'scripts', 'osfstorage', 'files_audit')
        try:
            os.makedirs(cls._audit_temp_path)
        except OSError:  # Path already exists
            pass
        storage_settings.AUDIT_TEMP_PATH = cls._audit_temp_path

    @classmethod
    def tearDownClass(cls):
        """Restore audit temp path.
        """
        super(TestFilesAudit, cls).tearDownClass()
        shutil.rmtree(cls._audit_temp_path)
        storage_settings.AUDIT_TEMP_PATH = cls._old_audit_temp_path

    @mock.patch('os.path.exists')
    @mock.patch('scripts.osfstorage.files_audit.container_primary')
    def test_download(self, mock_container, mock_exists):
        files_audit.audit_temp_path = os.path.join(storage_settings.AUDIT_TEMP_PATH)
        file_contents = ['fake', 'file', 'content']
        mock_obj = mock.Mock()
        mock_obj.fetch.return_value = iter(file_contents)
        mock_container.get_object.return_value = mock_obj
        mock_exists.return_value = False
        version = FileVersionFactory()
        version.metadata = {'sha256': 'dff32002043d7a4da7173d2034cb2f6856d10549bd8cc6d7e16d62f1304681f8'}  # fakefilecontent

        mock_open = mock.mock_open()
        with mock.patch('scripts.osfstorage.files_audit.open', mock_open, create=True):
            download_from_cloudfiles(version)

        mock_container.get_object.assert_called_with(version.location['object'])
        mock_open.assert_called_once_with(os.path.join(os.path.join(storage_settings.AUDIT_TEMP_PATH), version.location['object']), 'wb')

        handle = mock_open()
        assert_equal(handle.write.call_count, 3)
        for content in file_contents:
            handle.write.assert_any_call(content)

    @mock.patch('os.path.exists')
    @mock.patch('scripts.osfstorage.files_audit.container_primary')
    def test_download_exists(self, mock_container, mock_exists):
        mock_exists.return_value = True
        assert_false(mock_container.get_object.called)

    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.vault')
    def test_ensure_glacier(self, mock_vault, mock_download):
        glacier_id = 'iamarchived'
        version = FileVersionFactory()
        file_path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
        mock_download.return_value = file_path
        mock_vault.upload_archive.return_value = glacier_id
        ensure_glacier(version, dry_run=False)
        mock_vault.upload_archive.assert_called_with(file_path, description=version.location['object'])
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
