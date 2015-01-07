import os
import functools
from unittest import mock

import pytest

from tests.utils import async

from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import backup
from waterbutler.providers.osfstorage.tasks import parity

EMPTYFUNC = lambda *_, **__: None


class TestParityTask:

    def test_main_delays(self, monkeypatch):
        task = mock.Mock()
        monkeypatch.setattr(parity, '_parity_create_files', task)

        parity.main('The Best')

        task.delay.assert_called_once_with('The Best')

    def test_calls_create_parity(self, monkeypatch):
        create_parity = mock.Mock(return_value=[])
        monkeypatch.setattr(parity.asyncio, 'get_event_loop', mock.Mock())
        monkeypatch.setattr(parity.utils, 'create_parity_files', create_parity)

        parity._parity_create_files('Triangles')

        create_parity.assert_called_once_with(
            os.path.join(settings.FILE_PATH_COMPLETE, 'Triangles'),
            redundancy=settings.PARITY_REDUNDANCY
        )

    def test_creates_upload_futures(self, monkeypatch):
        paths = range(10)
        upload_parity = mock.Mock()
        monkeypatch.setattr(parity.asyncio, 'async', mock.Mock())
        monkeypatch.setattr(parity, '_upload_parity', upload_parity)
        monkeypatch.setattr(parity.asyncio, 'get_event_loop', mock.Mock())
        monkeypatch.setattr(parity.utils, 'create_parity_files', lambda *_, **__: paths)

        parity._parity_create_files('Triangles')

        for num in reversed(range(10)):
            upload_parity.assert_any_call(num)

    @async
    def test_uploads(self, monkeypatch, tmpdir):
        provider_mock = mock.MagicMock()
        tempfile = tmpdir.join('test.file')
        stream = parity.streams.FileStreamReader(tempfile)
        monkeypatch.setattr(parity.streams, 'FileStreamReader', lambda x: stream)
        monkeypatch.setattr(parity.provider_proxy, 'get', lambda: provider_mock)


        tempfile.write('foo')
        path = tempfile.strpath

        yield from parity._upload_parity(path)

        assert provider_mock.upload.called

        provider_mock.upload.assert_called_once_with(stream, path=os.path.split(path)[1])


    # @pytest.mark.skip
    # def test_retries_upload(self, monkeypatch):
    #     old = parity._parity_create_files
    #     new_parity = mock.Mock(side_effect=old)
    #     create_parity = mock.Mock(side_effect=NotImplementedError)

    #     monkeypatch.setattr(parity, '_parity_create_files', new_parity)
    #     monkeypatch.setattr(parity.asyncio, 'get_event_loop', mock.Mock())
    #     monkeypatch.setattr(parity.utils, 'create_parity_files', create_parity)
    #     monkeypatch.setattr(parity.utils, 'RetryUpload',
    #         functools.partial(
    #             parity.utils.RetryTask,
    #             attempts=10,
    #             init_delay=0,
    #             max_delay=0,
    #             backoff=0,
    #             warn_idx=settings.UPLOAD_RETRY_WARN_IDX,
    #             error_types=(Exception,),
    #         )
    #     )

    #     with pytest.raises(NotImplementedError):
    #         parity._parity_create_files.delay('Triangles')


class TestBackUpTask:

    def test_main_delays(self, monkeypatch):
        task = mock.Mock()
        monkeypatch.setattr(backup, '_push_file_archive', task)

        backup.main('The Best', 0, None)

        task.delay.assert_called_once_with('The Best', 0, None)

    def test_tries_upload(self, monkeypatch):
        mock_vault = mock.Mock()
        mock_vault.name = 'ThreePoint'
        mock_vault.upload_archive.return_value = 3
        monkeypatch.setattr(backup.vault_proxy, '_result', mock_vault)
        monkeypatch.setattr(backup, '_push_archive_complete', mock.Mock())

        backup._push_file_archive('Triangles', None, None)

        mock_vault.upload_archive.assert_called_once_with('Triangles', description='Triangles')


    def test_calls_complete(self, monkeypatch):
        mock_vault = mock.Mock()
        mock_complete = mock.Mock()
        mock_vault.name = 'ThreePoint'
        mock_vault.upload_archive.return_value = 3
        monkeypatch.setattr(backup.vault_proxy, '_result', mock_vault)
        monkeypatch.setattr(backup, '_push_archive_complete', mock_complete)

        backup._push_file_archive('Triangles', 0, None)

        mock_complete.delay.assert_called_once_with(0, None, {
            'vault': 'ThreePoint',
            'archive': 3
        })
