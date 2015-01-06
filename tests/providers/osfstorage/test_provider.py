import os
import io
import asyncio
from unittest import mock

import pytest
import aiohttpretty

from tests.utils import async

from waterbutler.core import streams
from waterbutler.core import exceptions
from waterbutler.providers.osfstorage import OSFStorageProvider
from waterbutler.providers.osfstorage.settings import FILE_PATH_COMPLETE


@pytest.fixture
def file_content():
    return b'sleepy'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_stream(file_like):
    return streams.FileStreamReader(file_like)


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {
        'access_key': 'Dont dead',
        'secret_key': 'open inside',
    }


@pytest.fixture
def settings():
    return {
        'justa': 'setting',
        'provider': 'mock',
        'callback': 'https://waterbutler.io',
        'metadata': 'https://waterbutler.io/metadata',
    }


@pytest.fixture
def provider_and_mock(monkeypatch, auth, credentials, settings):
    mock_provider = mock.MagicMock()
    mock_make_provider = mock.Mock(return_value=mock_provider)
    monkeypatch.setattr(OSFStorageProvider, 'make_provider', mock_make_provider)
    return OSFStorageProvider(auth, credentials, settings), mock_provider


@pytest.fixture
def provider(provider_and_mock):
    provider, _ = provider_and_mock
    return provider


@pytest.fixture
def osf_response():
    return {
        'data': {
            'path': 'test/path',
        },
        'settings': {
            'justa': 'settings'
        }
    }


@async
@pytest.mark.aiohttpretty
def test_download(monkeypatch, provider_and_mock, osf_response):
    provider, inner_provider = provider_and_mock
    aiohttpretty.register_json_uri('GET', 'https://waterbutler.io', body=osf_response)

    yield from provider.download(path='/unrelatedpath')

    assert provider.make_provider.called
    assert inner_provider.download.called

    inner_provider.download.assert_called_once_with(path='/test/path')
    provider.make_provider.assert_called_once_with(osf_response['settings'])


@async
@pytest.mark.aiohttpretty
def test_delete(monkeypatch, provider):
    aiohttpretty.register_uri('DELETE', 'https://waterbutler.io', status_code=200)

    yield from provider.delete(path='/unrelatedpath')

    aiohttpretty.has_call(method='DELETE', uri='https://waterbutler.io', parmas={'path': 'unrelatedpath'})


@async
@pytest.mark.aiohttpretty
def test_provider_metadata_empty(monkeypatch, provider):
    aiohttpretty.register_json_uri('GET', 'https://waterbutler.io/metadata', status_code=200, body=[])

    res = yield from provider.metadata(path='/unrelatedpath')

    assert res == []

    aiohttpretty.has_call(method='GET', uri='https://waterbutler.io', parmas={'path': 'unrelatedpath'})


@async
@pytest.mark.aiohttpretty
def test_provider_metadata(monkeypatch, provider):
    items = [
        {
            'name': 'foo',
            'path': '/foo',
            'kind': 'file'
        },
        {
            'name': 'bar',
            'path': '/bar',
            'kind': 'file'
        },
        {
            'name': 'baz',
            'path': '/baz',
            'kind': 'folder'
        }
    ]
    aiohttpretty.register_json_uri('GET', 'https://waterbutler.io/metadata', status=200, body=items)

    res = yield from provider.metadata(path='/unrelatedpath')

    assert isinstance(res, list)

    for item in res:
        assert isinstance(item, dict)
        assert item['name'] is not None
        assert item['path'] is not None
        assert item['provider'] == 'osfstorage'

    aiohttpretty.has_call(method='GET', uri='https://waterbutler.io', parmas={'path': 'unrelatedpath'})


@async
@pytest.mark.aiohttpretty
def test_upload(monkeypatch, provider_and_mock, file_stream):
    mock_move = asyncio.Future()
    provider, inner_provider = provider_and_mock
    basepath = 'waterbutler.providers.osfstorage.provider.{}'
    aiohttpretty.register_json_uri('POST', 'https://waterbutler.io', status=200, body={})


    mock_move.set_result({})
    inner_provider.move.return_value = mock_move
    monkeypatch.setattr(basepath.format('os.rename'), lambda *_: None)
    monkeypatch.setattr(basepath.format('settings.RUN_PARITY'), False)
    monkeypatch.setattr(basepath.format('uuid.uuid4'), lambda: 'uniquepath')

    res, created = yield from provider.upload(file_stream, '/foopath')

    assert created is False
    assert res['name'] == 'foopath'
    assert res['provider'] == 'osfstorage'

    inner_provider.upload.assert_called_once_with(file_stream, '/uniquepath')
    inner_provider.move.assert_called_once_with(inner_provider, {'path': '/uniquepath'}, {'path': '/' + file_stream.writers['sha256'].hexdigest})


@async
@pytest.mark.aiohttpretty
def test_upload_and_tasks(monkeypatch, provider_and_mock, file_stream):
    mock_parity = mock.Mock()
    mock_backup = mock.Mock()
    mock_move = asyncio.Future()
    provider, inner_provider = provider_and_mock
    basepath = 'waterbutler.providers.osfstorage.provider.{}'
    aiohttpretty.register_json_uri('POST', 'https://waterbutler.io', status=201, body={'version_id': 42})


    mock_move.set_result({})
    inner_provider.move.return_value = mock_move
    monkeypatch.setattr(basepath.format('backup.main'), mock_backup)
    monkeypatch.setattr(basepath.format('parity.main'), mock_parity)
    monkeypatch.setattr(basepath.format('settings.RUN_PARITY'), True)
    monkeypatch.setattr(basepath.format('os.rename'), lambda *_: None)
    monkeypatch.setattr(basepath.format('uuid.uuid4'), lambda: 'uniquepath')

    res, created = yield from provider.upload(file_stream, '/foopath')

    assert created is True
    assert res['name'] == 'foopath'
    assert res['provider'] == 'osfstorage'

    inner_provider.upload.assert_called_once_with(file_stream, '/uniquepath')
    mock_parity.assert_called_once_with(os.path.join(FILE_PATH_COMPLETE, file_stream.writers['sha256'].hexdigest))
    mock_backup.assert_called_once_with(os.path.join(FILE_PATH_COMPLETE, file_stream.writers['sha256'].hexdigest), 42, 'https://waterbutler.io')
    inner_provider.move.assert_called_once_with(inner_provider, {'path': '/uniquepath'}, {'path': '/' + file_stream.writers['sha256'].hexdigest})


