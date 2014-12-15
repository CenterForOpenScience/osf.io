import io
import hashlib

import pytest

from tests.utils import async
from tests.mocking import aiopretty

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions
from waterbutler.providers.contrib.dropbox import DropboxProvider


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def identity():
    return {
        'token': 'wrote harry potter',
        'folder': 'similar to a (w)rapper',
    }


@pytest.fixture
def provider(auth, identity):
    return DropboxProvider(auth, identity)


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
def folder_contents():
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
def folder_content():
    return {
        "size": "225.4KB",
        "rev": "35e97029684fe",
        "thumb_exists": False,
        "bytes": 230783,
        "modified": "Tue, 19 Jul 2011 21:55:38 +0000",
        "client_mtime": "Mon, 18 Jul 2011 18:04:35 +0000",
        "path": "/Getting_Started.pdf",
        "is_dir": False,
        "icon": "page_white_acrobat",
        "root": "dropbox",
        "mime_type": "application/pdf",
        "revision": 220823
    }


@async
@pytest.mark.aiopretty
def test_download(provider):
    url = provider.build_content_url('files', 'auto', provider.build_path('MUHTRANGLES'))
    aiopretty.register_uri('GET', url, body=b'I"ve had better')
    result = yield from provider.download('MUHTRANGLES')
    content = yield from result.response.read()
    assert content == b'I"ve had better'


@async
@pytest.mark.aiopretty
def test_download_not_found(provider):
    url = provider.build_content_url('files', 'auto', provider.build_path('MUHVECTORS'))
    aiopretty.register_uri('GET', url, status=404)
    with pytest.raises(exceptions.DownloadError):
        yield from provider.download('MUHVECTORS')


@async
@pytest.mark.aiopretty
def test_metadata(provider, folder_contents):
    url = provider.build_url('metadata', 'auto', provider.build_path(''))
    aiopretty.register_json_uri('GET', url, body=folder_contents)
    result = yield from provider.metadata('')

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['name'] == 'flower.jpg'


@async
@pytest.mark.aiopretty
def test_metadata_single(provider, folder_content):
    url = provider.build_url('metadata', 'auto', provider.build_path('phile'))
    aiopretty.register_json_uri('GET', url, body=folder_content)
    result = yield from provider.metadata('phile')

    assert isinstance(result, dict)
    assert result['name'] == 'Getting_Started.pdf'


@async
@pytest.mark.aiopretty
def test_metadata_missing(provider):
    url = provider.build_url('metadata', 'auto', provider.build_path('phile'))
    aiopretty.register_uri('GET', url, status=404)

    with pytest.raises(exceptions.FileNotFoundError):
        result = yield from provider.metadata('phile')


@async
@pytest.mark.aiopretty
def test_upload(provider, file_content, file_stream):
    path = 'phile'
    url = provider.build_content_url('files_put', 'auto', provider.build_path(path))
    aiopretty.register_uri('PUT', url, status=200)

    resp = yield from provider.upload(file_stream, path)

    assert resp.response.status == 200
    assert aiopretty.has_call(method='PUT', uri=url)


@async
@pytest.mark.aiopretty
def test_delete(provider):
    path = 'The past'
    url = provider.build_url('fileops', 'delete')
    data = {'folder': 'auto', 'path': provider.build_path(path)}

    aiopretty.register_uri('POST', url, status=200)

    yield from provider.delete(path)

    assert aiopretty.has_call(method='POST', uri=url, data=data)
