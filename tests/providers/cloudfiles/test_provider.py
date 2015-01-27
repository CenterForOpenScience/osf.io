import pytest

from unittest import mock
from tests.utils import async

import io
import json
import time
import hashlib

import furl
import aiohttp
import aiohttp.multidict
import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.cloudfiles import settings
from waterbutler.providers.cloudfiles import CloudFilesProvider
from waterbutler.providers.cloudfiles.provider import CloudFilesPath


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {
        'username': 'prince',
        'token': 'revolutionary',
        'region': 'iad',
    }


@pytest.fixture
def settings():
    return {'container': 'purple rain'}


@pytest.fixture
def provider(auth, credentials, settings):
    return CloudFilesProvider(auth, credentials, settings)


@pytest.fixture
def auth_json():
    return {
        "access": {
            "serviceCatalog": [
                {
                    "name": "cloudFiles",
                    "type": "object-store",
                    "endpoints": [
                        {
                            "publicURL": "https://storage101.iad3.clouddrive.com/v1/MossoCloudFS_926294",
                            "internalURL": "https://snet-storage101.iad3.clouddrive.com/v1/MossoCloudFS_926294",
                            "region": "IAD",
                            "tenantId": "MossoCloudFS_926294"
                        },
                    ]
                }
            ],
            "token": {
                "RAX-AUTH:authenticatedBy": [
                    "APIKEY"
                ],
                "tenant": {
                    "name": "926294",
                    "id": "926294"
                },
                "id": "2322f6b2322f4dbfa69802baf50b0832",
                "expires": "2014-12-17T09:12:26.069Z"
            },
            "user": {
                "name": "osf-production",
                "roles": [
                    {
                        "name": "object-store:admin",
                        "id": "10000256",
                        "description": "Object Store Admin Role for Account User"
                    },
                    {
                        "name": "compute:default",
                        "description": "A Role that allows a user access to keystone Service methods",
                        "id": "6",
                        "tenantId": "926294"
                    },
                    {
                        "name": "object-store:default",
                        "description": "A Role that allows a user access to keystone Service methods",
                        "id": "5",
                        "tenantId": "MossoCloudFS_926294"
                    },
                    {
                        "name": "identity:default",
                        "id": "2",
                        "description": "Default Role."
                    }
                ],
                "id": "secret",
                "RAX-AUTH:defaultRegion": "IAD"
            }
        }
    }


@pytest.fixture
def token(auth_json):
    return auth_json['access']['token']['id']


@pytest.fixture
def endpoint(auth_json):
    return auth_json['access']['serviceCatalog'][0]['endpoints'][0]['publicURL']


@pytest.fixture
def temp_url_key():
    return 'temporary beret'


@pytest.fixture
def mock_auth(auth_json):
    aiohttpretty.register_json_uri(
        'POST',
        settings.AUTH_URL,
        body=auth_json,
    )


@pytest.fixture
def mock_temp_key(endpoint, temp_url_key):
    aiohttpretty.register_uri(
        'HEAD',
        endpoint,
        status=204,
        headers={'X-Account-Meta-Temp-URL-Key': temp_url_key},
    )


@pytest.fixture
def mock_time(monkeypatch):
    mock_time = mock.Mock()
    mock_time.return_value = 10
    monkeypatch.setattr(time, 'time', mock_time)


@pytest.fixture
def connected_provider(provider, token, endpoint, temp_url_key, mock_time):
    provider.token = token
    provider.endpoint = endpoint
    provider.temp_url_key = temp_url_key.encode()
    return provider


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
def file_metadata():
    return aiohttp.multidict.CIMultiDict([
        ('LAST-MODIFIED', 'Thu, 25 Dec 2014 02:54:35 GMT'),
        ('CONTENT-LENGTH', '0'),
        ('ETAG', 'edfa12d00b779b4b37b81fe5b61b2b3f'),
        ('CONTENT-TYPE', 'text/html; charset=UTF-8'),
        ('X-TRANS-ID', 'txf876a4b088e3451d94442-00549b7c6aiad3'),
        ('DATE', 'Thu, 25 Dec 2014 02:54:34 GMT')
    ])


# Metadata Test Scenarios
# / (folder_root_empty)
# / (folder_root)
# /level1/  (folder_root_level1)
# /level1/level2/ (folder_root_level1_level2)
# /level1/level2/file2.file - (file_root_level1_level2_file2_txt)
# /level1_empty/ (folder_root_level1_empty)
# /similar (file_similar)
# /similar.name (file_similar_name)
# /does_not_exist (404)
# /does_not_exist/ (404)


@pytest.fixture
def folder_root_empty():
    return []


@pytest.fixture
def folder_root():
    return [
        {
            'last_modified': '2014-12-19T22:08:23.006360',
            'content_type': 'application/directory',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'name': 'level1',
            'bytes': 0
        },
        {
            'subdir': 'level1/'
        },
        {
            'last_modified': '2014-12-19T23:22:23.232240',
            'content_type': 'application/x-www-form-urlencoded;charset=utf-8',
            'hash': 'edfa12d00b779b4b37b81fe5b61b2b3f',
            'name': 'similar',
            'bytes': 190
        },
        {
            'last_modified': '2014-12-19T23:22:14.728640',
            'content_type': 'application/x-www-form-urlencoded;charset=utf-8',
            'hash': 'edfa12d00b779b4b37b81fe5b61b2b3f',
            'name': 'similar.file',
            'bytes': 190
        },
        {
            'last_modified': '2014-12-19T23:20:16.718860',
            'content_type': 'application/directory',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'name': 'level1_empty',
            'bytes': 0
        }
    ]


@pytest.fixture
def folder_root_level1():
    return [
        {
            'last_modified': '2014-12-19T22:08:26.958830',
            'content_type': 'application/directory',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'name': 'level1/level2',
            'bytes': 0
        },
        {
            'subdir': 'level1/level2/'
        }
    ]


@pytest.fixture
def folder_root_level1_level2():
    return [
        {
            'name': 'level1/level2/file2.txt',
            'content_type': 'application/x-www-form-urlencoded;charset=utf-8',
            'last_modified': '2014-12-19T23:25:22.497420',
            'bytes': 1365336,
            'hash': 'ebc8cdd3f712fd39476fb921d43aca1a'
        }
    ]


@pytest.fixture
def file_root_level1_level2_file2_txt():
    return aiohttp.multidict.CIMultiDict([
        ('ORIGIN', 'https://mycloud.rackspace.com'),
        ('CONTENT-LENGTH', '216945'),
        ('ACCEPT-RANGES', 'bytes'),
        ('LAST-MODIFIED', 'Mon, 22 Dec 2014 19:01:02 GMT'),
        ('ETAG', '44325d4f13b09f3769ede09d7c20a82c'),
        ('X-TIMESTAMP', '1419274861.04433'),
        ('CONTENT-TYPE', 'text/plain'),
        ('X-TRANS-ID', 'tx836375d817a34b558756a-0054987deeiad3'),
        ('DATE', 'Mon, 22 Dec 2014 20:24:14 GMT')
    ])


@pytest.fixture
def folder_root_level1_empty():
    return aiohttp.multidict.CIMultiDict([
        ('ORIGIN', 'https://mycloud.rackspace.com'),
        ('CONTENT-LENGTH', '0'),
        ('ACCEPT-RANGES', 'bytes'),
        ('LAST-MODIFIED', 'Mon, 22 Dec 2014 18:58:56 GMT'),
        ('ETAG', 'd41d8cd98f00b204e9800998ecf8427e'),
        ('X-TIMESTAMP', '1419274735.03160'),
        ('CONTENT-TYPE', 'application/directory'),
        ('X-TRANS-ID', 'txd78273e328fc4ba3a98e3-0054987eeeiad3'),
        ('DATE', 'Mon, 22 Dec 2014 20:28:30 GMT')
    ])


@pytest.fixture
def file_root_similar():
    return aiohttp.multidict.CIMultiDict([
        ('ORIGIN', 'https://mycloud.rackspace.com'),
        ('CONTENT-LENGTH', '190'),
        ('ACCEPT-RANGES', 'bytes'),
        ('LAST-MODIFIED', 'Fri, 19 Dec 2014 23:22:24 GMT'),
        ('ETAG', 'edfa12d00b779b4b37b81fe5b61b2b3f'),
        ('X-TIMESTAMP', '1419031343.23224'),
        ('CONTENT-TYPE', 'application/x-www-form-urlencoded;charset=utf-8'),
        ('X-TRANS-ID', 'tx7cfeef941f244807aec37-005498754diad3'),
        ('DATE', 'Mon, 22 Dec 2014 19:47:25 GMT')
    ])


@pytest.fixture
def file_root_similar_name():
    return aiohttp.multidict.CIMultiDict([
        ('ORIGIN', 'https://mycloud.rackspace.com'),
        ('CONTENT-LENGTH', '190'),
        ('ACCEPT-RANGES', 'bytes'),
        ('LAST-MODIFIED', 'Mon, 22 Dec 2014 19:07:12 GMT'),
        ('ETAG', 'edfa12d00b779b4b37b81fe5b61b2b3f'),
        ('X-TIMESTAMP', '1419275231.66160'),
        ('CONTENT-TYPE', 'application/x-www-form-urlencoded;charset=utf-8'),
        ('X-TRANS-ID', 'tx438cbb32b5344d63b267c-0054987f3biad3'),
        ('DATE', 'Mon, 22 Dec 2014 20:29:47 GMT')
    ])


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, connected_provider):
        path = CloudFilesPath('/lets-go-crazy')
        body = b'dearly-beloved'
        url = connected_provider.sign_url(path)
        aiohttpretty.register_uri('GET', url, body=body)
        result = yield from connected_provider.download(str(path))
        content = yield from result.response.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_download_accept_url(self, connected_provider):
        path = CloudFilesPath('/lets-go-crazy')
        body = b'dearly-beloved'
        url = connected_provider.sign_url(path)
        parsed_url = furl.furl(url)
        parsed_url.args['filename'] = 'lets-go-crazy'
        result = yield from connected_provider.download(str(path), accept_url=True)
        assert result == parsed_url.url
        aiohttpretty.register_uri('GET', url, body=body)
        response = yield from aiohttp.request('GET', url)
        content = yield from response.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, connected_provider):
        path = CloudFilesPath('/lets-go-crazy')
        url = connected_provider.sign_url(path)
        aiohttpretty.register_uri('GET', url, status=404)
        with pytest.raises(exceptions.DownloadError):
            yield from connected_provider.download(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_upload(self, connected_provider, file_content, file_stream, file_metadata):
        path = CloudFilesPath('/foo.bar')
        content_md5 = hashlib.md5(file_content).hexdigest()
        metadata_url = connected_provider.build_url(path.path)
        url = connected_provider.sign_url(path, 'PUT')
        aiohttpretty.register_uri(
            'HEAD',
            metadata_url,
            responses=[
                {'status': 404},
                {'headers': file_metadata},
            ]
        )
        aiohttpretty.register_uri('PUT', url, status=200, headers={'ETag': '"{}"'.format(content_md5)})
        metadata, created = yield from connected_provider.upload(file_stream, str(path))

        assert metadata['kind'] == 'file'
        assert created
        assert aiohttpretty.has_call(method='PUT', uri=url)
        assert aiohttpretty.has_call(method='HEAD', uri=metadata_url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete(self, connected_provider):
        path = CloudFilesPath('/delete.file')
        url = connected_provider.build_url(path.path)
        aiohttpretty.register_uri('DELETE', url, status=204)
        yield from connected_provider.delete(str(path))

        assert aiohttpretty.has_call(method='DELETE', uri=url)


class TestMetadata:

    @async
    def test_metadata_invalid_root_path(self, connected_provider):
        path = ''
        with pytest.raises(ValueError):
            yield from connected_provider.metadata(path)

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root_empty(self, connected_provider, folder_root_empty):
        path = CloudFilesPath('/')
        body = json.dumps(folder_root_empty).encode('utf-8')
        url = connected_provider.build_url(path.path, prefix=path.path, delimiter='/')
        aiohttpretty.register_uri('GET', url, status=200, body=body)
        result = yield from connected_provider.metadata(str(path))

        assert len(result) == 0
        assert result == []

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root(self, connected_provider, folder_root):
        path = CloudFilesPath('/')
        body = json.dumps(folder_root).encode('utf-8')
        url = connected_provider.build_url('', prefix=path.path, delimiter='/')
        aiohttpretty.register_uri('GET', url, status=200, body=body)
        result = yield from connected_provider.metadata(str(path))

        assert len(result) == 4
        assert result[0]['name'] == 'level1'
        assert result[0]['path'] == '/level1/'
        assert result[0]['kind'] == 'folder'
        assert result[1]['name'] == 'similar'
        assert result[1]['path'] == '/similar'
        assert result[1]['kind'] == 'file'
        assert result[2]['name'] == 'similar.file'
        assert result[2]['path'] == '/similar.file'
        assert result[2]['kind'] == 'file'
        assert result[3]['name'] == 'level1_empty'
        assert result[3]['path'] == '/level1_empty/'
        assert result[3]['kind'] == 'folder'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root_level1(self, connected_provider, folder_root_level1):
        path = CloudFilesPath('/level1/')
        body = json.dumps(folder_root_level1).encode('utf-8')
        url = connected_provider.build_url('', prefix=path.path, delimiter='/')
        aiohttpretty.register_uri('GET', url, status=200, body=body)
        result = yield from connected_provider.metadata(str(path))

        assert len(result) == 1
        assert result[0]['name'] == 'level2'
        assert result[0]['path'] == '/level1/level2/'
        assert result[0]['kind'] == 'folder'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root_level1_level2(self, connected_provider, folder_root_level1_level2):
        path = CloudFilesPath('/level1/level2/')
        body = json.dumps(folder_root_level1_level2).encode('utf-8')
        url = connected_provider.build_url('', prefix=path.path, delimiter='/')
        aiohttpretty.register_uri('GET', url, status=200, body=body)
        result = yield from connected_provider.metadata(str(path))

        assert len(result) == 1
        assert result[0]['name'] == 'file2.txt'
        assert result[0]['path'] == '/level1/level2/file2.txt'
        assert result[0]['kind'] == 'file'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_root_level1_level2_file2_txt(self, connected_provider, file_root_level1_level2_file2_txt):
        path = CloudFilesPath('/level1/level2/file2.txt')
        url = connected_provider.build_url(path.path)
        aiohttpretty.register_uri('HEAD', url, status=200, headers=file_root_level1_level2_file2_txt)
        result = yield from connected_provider.metadata(str(path))

        assert result['name'] == 'file2.txt'
        assert result['path'] == '/level1/level2/file2.txt'
        assert result['kind'] == 'file'
        assert result['contentType'] == 'text/plain'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root_level1_empty(self, connected_provider, folder_root_level1_empty):
        path = CloudFilesPath('/level1_empty/')
        folder_url = connected_provider.build_url('', prefix=path.path, delimiter='/')
        folder_body = json.dumps([]).encode('utf-8')
        file_url = connected_provider.build_url(path.path.rstrip('/'))
        aiohttpretty.register_uri('GET', folder_url, status=200, body=folder_body)
        aiohttpretty.register_uri('HEAD', file_url, status=200, headers=folder_root_level1_empty)
        result = yield from connected_provider.metadata(str(path))

        assert result == []

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_root_similar(self, connected_provider, file_root_similar):
        path = CloudFilesPath('/similar')
        url = connected_provider.build_url(path.path)
        aiohttpretty.register_uri('HEAD', url, status=200, headers=file_root_similar)
        result = yield from connected_provider.metadata(str(path))

        assert result['name'] == 'similar'
        assert result['path'] == '/similar'
        assert result['kind'] == 'file'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_root_similar_name(self, connected_provider, file_root_similar_name):
        path = CloudFilesPath('/similar.file')
        url = connected_provider.build_url(path.path)
        aiohttpretty.register_uri('HEAD', url, status=200, headers=file_root_similar_name)
        result = yield from connected_provider.metadata(str(path))

        assert result['name'] == 'similar.file'
        assert result['path'] == '/similar.file'
        assert result['kind'] == 'file'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_does_not_exist(self, connected_provider):
        path = CloudFilesPath('/does_not.exist')
        url = connected_provider.build_url(path.path)
        aiohttpretty.register_uri('HEAD', url, status=404)
        with pytest.raises(exceptions.MetadataError):
            yield from connected_provider.metadata(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_does_not_exist(self, connected_provider):
        path = CloudFilesPath('/does_not_exist/')
        folder_url = connected_provider.build_url('', prefix=path.path, delimiter='/')
        folder_body = json.dumps([]).encode('utf-8')
        file_url = connected_provider.build_url(path.path.rstrip('/'))
        aiohttpretty.register_uri('GET', folder_url, status=200, body=folder_body)
        aiohttpretty.register_uri('HEAD', file_url, status=404)
        with pytest.raises(exceptions.MetadataError):
            yield from connected_provider.metadata(str(path))


class TestOperations:

    def test_can_intra_copy(self, connected_provider):
        assert connected_provider.can_intra_copy(connected_provider)


    def test_can_intra_move(self, connected_provider):
        assert connected_provider.can_intra_move(connected_provider)
