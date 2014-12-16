import pytest

from tests.utils import async
from tests.mocking import aiopretty

import io
import hashlib
from waterbutler import streams
from waterbutler.providers import exceptions
from waterbutler.providers.contrib.s3 import S3Provider


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
    return {'bucket': 'that kerning'}


@pytest.fixture
def provider(auth, credentials, settings):
    return S3Provider(auth, credentials, settings)


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
def folder_metadata():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Name>bucket</Name>
            <Prefix/>
            <Marker/>
            <MaxKeys>1000</MaxKeys>
            <IsTruncated>false</IsTruncated>
            <Contents>
                <Key>my-image.jpg</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>434234</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
            <Contents>
            <Key>my-third-image.jpg</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;1b2cf535f27731c974343645a3985328&quot;</ETag>
                <Size>64994</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
            <CommonPrefixes>
                <Prefix>photos/</Prefix>
            </CommonPrefixes>
        </ListBucketResult>'''


@pytest.fixture
def file_metadata():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Name>bucket</Name>
            <Prefix/>
            <Marker/>
            <MaxKeys>1000</MaxKeys>
            <IsTruncated>false</IsTruncated>
            <Contents>
                <Key>my-image.jpg</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>434234</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
        </ListBucketResult>'''


@async
@pytest.mark.aiopretty
def test_download(provider):
    url = provider.bucket.new_key('muhtriangle').generate_url(100)
    aiopretty.register_uri('GET', url, body=b'delicious')

    result = yield from provider.download('muhtriangle')
    content = yield from result.response.read()

    assert content == b'delicious'


@async
@pytest.mark.aiopretty
def test_download_not_found(provider):
    url = provider.bucket.new_key('muhtriangle').generate_url(100)
    aiopretty.register_uri('GET', url, status=404)

    with pytest.raises(exceptions.DownloadError):
        yield from provider.download('muhtriangle')


@async
@pytest.mark.aiopretty
def test_download_no_name(provider):
    with pytest.raises(exceptions.ProviderError):
        yield from provider.download('')


@async
@pytest.mark.aiopretty
def test_metadata_folder(provider, folder_metadata):
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, body=folder_metadata, headers={'Content-Type': 'application/xml'})
    result = yield from provider.metadata('')

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['name'] == 'my-image.jpg'
    assert result[1]['extra']['md5'] == '1b2cf535f27731c974343645a3985328'


@async
@pytest.mark.aiopretty
def test_metadata_file(provider, file_metadata):
    name = 'my-image.jpg'
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, body=file_metadata, headers={'Content-Type': 'application/xml'})
    result = yield from provider.metadata(name)

    assert isinstance(result, dict)

    assert result['name'] == name
    assert result['extra']['md5'] == 'fba9dede5f27731c9771645a39863328'


@async
@pytest.mark.aiopretty
def test_metadata_file_missing(provider):
    name = 'notfound.txt'
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, status=404, headers={'Content-Type': 'application/xml'})

    with pytest.raises(exceptions.MetadataError):
        yield from provider.metadata(name)


@async
@pytest.mark.aiopretty
def test_upload(provider, file_content, file_stream, file_metadata):
    path = 'foobah'
    content_md5 = hashlib.md5(file_content).hexdigest()
    url = provider.bucket.new_key(path).generate_url(100, 'PUT')
    aiopretty.register_uri('PUT', url, status=200, headers={'ETag': '"{}"'.format(content_md5)})
    metadata_url = provider.bucket.generate_url(100, 'GET')
    aiopretty.register_uri('GET', metadata_url, body=file_metadata, headers={'Content-Type': 'application/xml'})

    resp = yield from provider.upload(file_stream, path)

    assert resp['kind'] == 'file'
    assert aiopretty.has_call(method='PUT', uri=url)
    assert aiopretty.has_call(method='GET', uri=metadata_url)


@async
@pytest.mark.aiopretty
def test_copy(provider):
    source_path = 'source'
    dest_path = 'dest'
    headers = {'x-amz-copy-source': '/{}/{}'.format(provider.settings['bucket'], source_path)}
    url = provider.bucket.new_key(dest_path).generate_url(100, 'PUT', headers=headers)
    aiopretty.register_uri('PUT', url, status=200)

    resp = yield from provider.copy(provider, {'path': source_path}, {'path': dest_path})

    assert resp.response.status == 200
    assert aiopretty.has_call(method='PUT', uri=url, headers=headers)


@async
@pytest.mark.aiopretty
def test_upload_update(provider, file_content, file_stream, file_metadata):
    path = 'foobah'
    content_md5 = hashlib.md5(file_content).hexdigest()
    url = provider.bucket.new_key(path).generate_url(100, 'PUT')
    aiopretty.register_uri('PUT', url, status=201, headers={'ETag': '"{}"'.format(content_md5)})
    metadata_url = provider.bucket.generate_url(100, 'GET')
    aiopretty.register_uri('GET', metadata_url, body=file_metadata, headers={'Content-Type': 'application/xml'})

    resp = yield from provider.upload(file_stream, path)

    assert resp['kind'] == 'file'
    assert aiopretty.has_call(method='PUT', uri=url)
    assert aiopretty.has_call(method='GET', uri=metadata_url)


@async
@pytest.mark.aiopretty
def test_delete(provider):
    path = 'My Ex'
    url = provider.bucket.new_key(path).generate_url(100, 'DELETE')
    aiopretty.register_uri('DELETE', url, status=200)

    yield from provider.delete(path)

    assert aiopretty.has_call(method='DELETE', uri=url)
