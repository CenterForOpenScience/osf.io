# -*- coding: utf-8 -*-
import os
import shutil

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from addons.osfstorage.tests.factories import FileVersionFactory
from scripts.osfstorage import settings as storage_settings
from scripts.osfstorage import files_audit
from scripts.osfstorage.files_audit import Context, ensure_parity, ensure_glacier, download_from_cloudfiles


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
        cls.ctx = Context()
        cls.ctx.dry_run = False
        cls.ctx.audit_temp_path = cls._audit_temp_path
        storage_settings.AUDIT_TEMP_PATH = cls._audit_temp_path

    @classmethod
    def tearDownClass(cls):
        """Restore audit temp path.
        """
        super(TestFilesAudit, cls).tearDownClass()
        shutil.rmtree(cls._audit_temp_path)
        storage_settings.AUDIT_TEMP_PATH = cls._old_audit_temp_path

    @mock.patch('os.path.exists', return_value=False)
    def test_download(self, mock_exists):
        path = os.path.join(storage_settings.AUDIT_TEMP_PATH, 'test')
        file_contents = ['fake', 'file', 'content']
        self.ctx.container_primary = mock.Mock()
        self.ctx.container_primary.get_object.return_value.fetch.return_value = iter(file_contents)
        version = FileVersionFactory()
        version.metadata = {'sha256': 'dff32002043d7a4da7173d2034cb2f6856d10549bd8cc6d7e16d62f1304681f8'}  # fakefilecontent

        mock_open = mock.mock_open()
        with mock.patch('scripts.osfstorage.files_audit.open', mock_open, create=True):
            download_from_cloudfiles(self.ctx, version, path)

        self.ctx.container_primary.get_object.assert_called_with(version.location['object'])
        mock_open.assert_called_once_with(os.path.join(path, version.location['object']), 'wb')

        handle = mock_open()
        assert_equal(handle.write.call_count, 3)
        for content in file_contents:
            handle.write.assert_any_call(content)

    @mock.patch('os.remove')
    @mock.patch('os.path.getsize', return_value=files_audit.GLACIER_SINGLE_OPERATION_THRESHOLD + 1)  # 100 MB + 1 Byte
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    @mock.patch('scripts.osfstorage.files_audit.glacier_sync_multipart_upload')
    def test_ensure_glacier_is_multipart(self, mock_multipart_upload, mock_download, mock_getsize, mock_remove):
        path = os.path.join(storage_settings.AUDIT_TEMP_PATH, 'test')
        glacier_id = 'omgitsanid'
        glacier_vault_name = 'foo_bar'
        version = FileVersionFactory()
        file_path = os.path.join(path, version.location['object'])
        mock_download.return_value = file_path
        mock_multipart_upload.return_value = glacier_id
        self.ctx.vault = mock.Mock()
        self.ctx.vault.name = glacier_vault_name

        ensure_glacier(self.ctx, version, path)
        mock_multipart_upload.assert_called_with(
            self.ctx,
            version,
            file_path,
            files_audit.GLACIER_SINGLE_OPERATION_THRESHOLD + 1  # 100 MB + 1 Byte
        )
        version.reload()
        assert_equal(version.metadata['archive'], glacier_id)
        assert_equal(version.metadata['vault'], glacier_vault_name)

    @mock.patch('os.remove')
    @mock.patch('os.path.getsize', return_value=len('hello world'))
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    def test_ensure_glacier_not_multipart(self, mock_download, mock_getsize, mock_remove):
        path = os.path.join(storage_settings.AUDIT_TEMP_PATH, 'test')
        glacier_id = 'iamarchived'
        glacier_vault_name = 'foo_bar'
        version = FileVersionFactory()
        file_path = os.path.join(path, version.location['object'])
        mock_download.return_value = file_path
        self.ctx.vault = mock.Mock()
        self.ctx.vault.name = glacier_vault_name
        self.ctx.vault.upload_archive.return_value.id = glacier_id

        with mock.patch('scripts.osfstorage.files_audit.open', mock.mock_open(read_data='hello world'), create=True) as mfp:
            ensure_glacier(self.ctx, version, path)

        mfp.assert_called_once_with(file_path, 'rb')
        self.ctx.vault.upload_archive.assert_called_with(
            vaultName=storage_settings.GLACIER_VAULT_NAME,
            archiveDescription=version.location['object'],
            body=mfp(),
        )
        version.reload()
        assert_equal(version.metadata['archive'], glacier_id)
        assert_equal(version.metadata['vault'], glacier_vault_name)

    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    def test_ensure_glacier_metadata(self, mock_download):
        path = os.path.join(storage_settings.AUDIT_TEMP_PATH, 'test')
        version = FileVersionFactory()
        version.metadata['archive'] = 'foo'
        version.save()
        self.ctx.vault = mock.Mock()
        ensure_glacier(self.ctx, version, path)
        assert_false(self.ctx.vault.upload_archive.called)

    @mock.patch('os.remove')
    @mock.patch('scripts.osfstorage.files_audit.storage_utils.create_parity_files')
    @mock.patch('scripts.osfstorage.files_audit.download_from_cloudfiles')
    def test_ensure_parity_metadata(self, mock_download, mock_create_parity, mock_remove):
        path = os.path.join(storage_settings.AUDIT_TEMP_PATH, 'test')
        self.ctx.container_parity = mock.Mock()
        self.ctx.container_parity.list_all.return_value = []
        parity_results = [('/foo/bar{}'.format(i), str(i)) for i in range(8)]
        mock_create_parity.return_value = parity_results
        version = FileVersionFactory()

        ensure_parity(self.ctx, version, path)

        assert_equal(len(self.ctx.container_parity.create.call_args_list), 8)
        version.reload()
        assert_equal(version.metadata['parity']['redundancy'], storage_settings.PARITY_REDUNDANCY)
        assert_equal(
            sorted(version.metadata['parity']['files'], key=lambda datum: datum['name']),
            sorted([{'name': os.path.split(r[0])[1], 'sha256': r[1]} for r in parity_results], key=lambda datum: datum['name'])
        )
