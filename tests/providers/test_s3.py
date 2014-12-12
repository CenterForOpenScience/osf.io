import pytest

from tests.utils import async
from tests.mocking import aiopretty

import io
import os
import json

from waterbutler import exceptions
from waterbutler.providers import core
from waterbutler.providers.contrib.s3 import S3Provider


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def identity():
    return {
        'access_key': 'Dont dead',
        'secret_key': 'open inside',
        'bucket': 'that kerning',
    }


@pytest.fixture
def provider(auth, identity):
    return S3Provider(auth, identity)


@pytest.fixture
def file_content():
    return b'sleepy'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_wrapper(file_like):
    return core.FileStream(file_like)


@pytest.fixture
def bucket_contents():
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
def bucket_content():
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
    with pytest.raises(exceptions.FileNotFoundError):
        yield from provider.download('muhtriangle')


@async
@pytest.mark.aiopretty
def test_download_no_name(provider):
    with pytest.raises(exceptions.ProviderError):
        yield from provider.download('')


@async
@pytest.mark.aiopretty
def test_metadata(provider, bucket_contents):
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, body=bucket_contents, headers={'Content-Type': 'application/xml'})
    result = yield from provider.metadata('')

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['name'] == 'my-image.jpg'
    assert result[1]['extra']['md5'] == '1b2cf535f27731c974343645a3985328'


@async
@pytest.mark.aiopretty
def test_metadata_single(provider, bucket_content):
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, body=bucket_content, headers={'Content-Type': 'application/xml'})
    result = yield from provider.metadata('')

    assert isinstance(result, dict)
    assert result['name'] == 'my-image.jpg'
    assert result['extra']['md5'] == 'fba9dede5f27731c9771645a39863328'


@async
@pytest.mark.aiopretty
def test_metadata_missing(provider, bucket_content):
    url = provider.bucket.generate_url(100)
    aiopretty.register_uri('GET', url, status=404, headers={'Content-Type': 'application/xml'})

    with pytest.raises(exceptions.FileNotFoundError):
        result = yield from provider.metadata('')


@async
@pytest.mark.aiopretty
def test_upload(provider, file_wrapper):
    path = 'foobah'
    url = provider.bucket.new_key(path).generate_url(100, 'PUT')
    aiopretty.register_uri('PUT', url, status=200)

    resp = yield from provider.upload(file_wrapper, path)

    assert resp.response.status == 200
    assert aiopretty.has_call(method='PUT', uri=url)


@async
@pytest.mark.aiopretty
def test_upload_update(provider, file_wrapper):
    path = 'foobah'
    url = provider.bucket.new_key(path).generate_url(100, 'PUT')
    aiopretty.register_uri('PUT', url, status=201)

    resp = yield from provider.upload(file_wrapper, path)

    assert resp.response.status == 201
    assert aiopretty.has_call(method='PUT', uri=url)


@async
@pytest.mark.aiopretty
def test_delete(provider):
    path = 'My Ex wife'
    url = provider.bucket.new_key(path).generate_url(100, 'DELETE')

    aiopretty.register_uri('DELETE', url, status=200)

    yield from provider.delete(path)

    assert aiopretty.has_call(method='DELETE', uri=url)
