import pytest

from tests.utils import async

import io

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.dropbox.provider import DropboxProvider
from waterbutler.dropbox.metadata import DropboxMetadata


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {'token': 'wrote harry potter'}


@pytest.fixture
def settings():
    return {'folder': '/Photos'}


@pytest.fixture
def provider(auth, credentials, settings):
    return DropboxProvider(auth, credentials, settings)


@pytest.fixture
def file_content():
    return b'SLEEP IS FOR THE WEAK GO SERVE STREAMS'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_stream(file_like):
    return streams.FileStreamReader(file_like)


@pytest.fixture
def folder_metadata():
    return {
        "size": "0 bytes",
        "hash": "37eb1ba1849d4b0fb0b28caf7ef3af52",
        "bytes": 0,
        "thumb_exists": False,
        "rev": "714f029684fe",
        "modified": "Wed, 27 Apr 2011 22:18:51 +0000",
        "path": "/Photos",
        "is_dir": True,
        "icon": "folder",
        "root": "dropbox",
        "contents": [
            {
                "size": "2.3 MB",
                "rev": "38af1b183490",
                "thumb_exists": True,
                "bytes": 2453963,
                "modified": "Mon, 07 Apr 2014 23:13:16 +0000",
                "client_mtime": "Thu, 29 Aug 2013 01:12:02 +0000",
                "path": "/Photos/flower.jpg",
                "photo_info": {
                "lat_long": [
                    37.77256666666666,
                    -122.45934166666667
                ],
                "time_taken": "Wed, 28 Aug 2013 18:12:02 +0000"
                },
                "is_dir": False,
                "icon": "page_white_picture",
                "root": "dropbox",
                "mime_type": "image/jpeg",
                "revision": 14511
            }
        ],
        "revision": 29007
    }


@pytest.fixture
def file_metadata():
    return {
        "size": "225.4KB",
        "rev": "35e97029684fe",
        "thumb_exists": False,
        "bytes": 230783,
        "modified": "Tue, 19 Jul 2011 21:55:38 +0000",
        "client_mtime": "Mon, 18 Jul 2011 18:04:35 +0000",
        "path": "/Photos/Getting_Started.pdf",
        "is_dir": False,
        "icon": "page_white_acrobat",
        "root": "dropbox",
        "mime_type": "application/pdf",
        "revision": 220823
    }


@async
@pytest.mark.aiohttpretty
def test_download(provider):
    url = provider.build_content_url('files', 'auto', provider.build_path('MUHTRANGLES'))
    aiohttpretty.register_uri('GET', url, body=b'I"ve had better')
    result = yield from provider.download('MUHTRANGLES')
    content = yield from result.response.read()
    assert content == b'I"ve had better'


@async
@pytest.mark.aiohttpretty
def test_download_not_found(provider):
    url = provider.build_content_url('files', 'auto', provider.build_path('MUHVECTORS'))
    aiohttpretty.register_uri('GET', url, status=404)
    with pytest.raises(exceptions.DownloadError):
        yield from provider.download('MUHVECTORS')


@async
@pytest.mark.aiohttpretty
def test_metadata(provider, folder_metadata):
    url = provider.build_url('metadata', 'auto', provider.build_path(''))
    aiohttpretty.register_json_uri('GET', url, body=folder_metadata)
    result = yield from provider.metadata('')

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['name'] == 'flower.jpg'


@async
@pytest.mark.aiohttpretty
def test_metadata_single(provider, file_metadata):
    url = provider.build_url('metadata', 'auto', provider.build_path('phile'))
    aiohttpretty.register_json_uri('GET', url, body=file_metadata)
    result = yield from provider.metadata('phile')

    assert isinstance(result, dict)
    assert result['name'] == 'Getting_Started.pdf'


@async
@pytest.mark.aiohttpretty
def test_metadata_missing(provider):
    url = provider.build_url('metadata', 'auto', provider.build_path('phile'))
    aiohttpretty.register_uri('GET', url, status=404)

    with pytest.raises(exceptions.MetadataError):
        result = yield from provider.metadata('phile')


@async
@pytest.mark.aiohttpretty
def test_upload(provider, file_metadata, file_stream, settings):
    path = 'phile'
    url = provider.build_content_url('files_put', 'auto', provider.build_path(path))
    aiohttpretty.register_json_uri('PUT', url, status=200, body=file_metadata)

    metadata = yield from provider.upload(file_stream, path)
    expected = DropboxMetadata(file_metadata, settings['folder']).serialized()
    assert metadata == expected

    assert aiohttpretty.has_call(method='PUT', uri=url)


@async
@pytest.mark.aiohttpretty
def test_delete(provider):
    path = 'The past'
    url = provider.build_url('fileops', 'delete')
    data = {'root': 'auto', 'path': provider.build_path(path)}

    aiohttpretty.register_uri('POST', url, status=200)

    yield from provider.delete(path)

    assert aiohttpretty.has_call(method='POST', uri=url, data=data)