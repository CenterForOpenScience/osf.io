import os
import asyncio
import functools
from unittest import mock

import pytest

from tests.utils import async

from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import utils
from waterbutler.providers.osfstorage.tasks import backup
from waterbutler.providers.osfstorage.tasks import parity
from waterbutler.providers.osfstorage.tasks import exceptions
from waterbutler.providers.osfstorage import settings as osf_settings


@pytest.fixture
def credentials():
    return {
    }


@pytest.fixture
def settings():
    return {
        'storage': {
            'provider': 'cloud',
            'container': 'butt',
        },
    }


class TestParityTask:

    def test_main_delays(self, monkeypatch, credentials, settings):
        task = mock.Mock()
        monkeypatch.setattr(parity, '_parity_create_files', task)

        fut = parity.main('The Best', credentials, settings)
        loop = asyncio.get_event_loop().run_until_complete(fut)

        task.delay.assert_called_once_with('The Best', credentials, settings)

    def test_creates_upload_futures(self, monkeypatch, credentials, settings):
        paths = range(10)
        future = asyncio.Future()
        future.set_result(None)
        mock_upload_parity = mock.Mock()
        mock_upload_parity.return_value = future
        mock_create_parity = mock.Mock(return_value=paths)
        monkeypatch.setattr(parity, '_upload_parity', mock_upload_parity)
        monkeypatch.setattr(parity.utils, 'create_parity_files', mock_create_parity)

        parity._parity_create_files('Triangles', credentials, settings)

        mock_create_parity.assert_called_once_with(
            os.path.join(osf_settings.FILE_PATH_COMPLETE, 'Triangles'),
            redundancy=osf_settings.PARITY_REDUNDANCY,
        )
        for num in reversed(range(10)):
            mock_upload_parity.assert_any_call(num, credentials, settings)

    @async
    def test_uploads(self, monkeypatch, tmpdir):
        mock_provider = mock.MagicMock()
        tempfile = tmpdir.join('test.file')
        stream = parity.streams.FileStreamReader(tempfile)
        monkeypatch.setattr(parity.streams, 'FileStreamReader', lambda x: stream)
        mock_make_provider = mock.Mock()
        mock_make_provider.return_value = mock_provider
        monkeypatch.setattr(parity, 'make_provider', mock_make_provider)

        tempfile.write('foo')
        path = tempfile.strpath

        yield from parity._upload_parity(path, {}, {})

        assert mock_provider.upload.called

        mock_provider.upload.assert_called_once_with(
            stream,
            path='/' + os.path.split(path)[1],
        )

    def test_exceptions_get_raised(self, monkeypatch):
        mock_sp_call = mock.Mock(return_value=7)
        monkeypatch.setattr(utils.subprocess, 'call', mock_sp_call)
        path = 'foo/bar/baz'
        args = ['par2', 'c', '-r5', 'baz.par2', path]

        with pytest.raises(exceptions.ParchiveError) as e:
            utils.create_parity_files(path)

            assert e.value == '{0} failed with code {1}'.format(' '.join(args), 7)

            with open(os.devnull, 'wb') as DEVNULL:
                mock_sp_call.assert_called_once_with(args, stdout=DEVNULL, stderr=DEVNULL)


class TestBackUpTask:

    def test_main_delays(self, monkeypatch):
        task = mock.Mock()
        monkeypatch.setattr(backup, '_push_file_archive', task)

        fut = backup.main('The Best', 0, None, {}, {})
        asyncio.get_event_loop().run_until_complete(fut)

        task.delay.assert_called_once_with('The Best', 0, None, {}, {})

    def test_tries_upload(self, monkeypatch):
        mock_vault = mock.Mock()
        mock_vault.name = 'ThreePoint'
        mock_vault.upload_archive.return_value = 3
        mock_get_vault = mock.Mock()
        mock_get_vault.return_value = mock_vault
        mock_complete = mock.Mock()
        monkeypatch.setattr(backup, 'get_vault', mock_get_vault)
        monkeypatch.setattr(backup, '_push_archive_complete', mock_complete)

        backup._push_file_archive('Triangles', None, None, {}, {})

        mock_vault.upload_archive.assert_called_once_with('Triangles', description='Triangles')

    def test_calls_complete(self, monkeypatch, credentials, settings):
        mock_vault = mock.Mock()
        mock_complete = mock.Mock()
        mock_vault.name = 'ThreePoint'
        mock_vault.upload_archive.return_value = 3
        mock_get_vault = mock.Mock()
        mock_get_vault.return_value = mock_vault
        monkeypatch.setattr(backup, 'get_vault', mock_get_vault)
        monkeypatch.setattr(backup, '_push_archive_complete', mock_complete)

        backup._push_file_archive('Triangles', 0, None, credentials, settings)

        mock_complete.delay.assert_called_once_with(
            0,
            None,
            {
                'vault': 'ThreePoint',
                'archive': 3
            },
        )
