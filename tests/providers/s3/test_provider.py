import pytest

from tests.utils import async

import io
import hashlib

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.s3 import S3Provider
from waterbutler.providers.s3.provider import S3Path
from waterbutler.providers.s3.metadata import S3FileMetadata
from waterbutler.providers.s3.metadata import S3FolderMetadata


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
def just_a_folder_metadata():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Name>bucket</Name>
            <Prefix/>
            <Marker/>
            <MaxKeys>1000</MaxKeys>
            <IsTruncated>false</IsTruncated>
            <Contents>
                <Key>naptime/</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>0</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
        </ListBucketResult>'''


@pytest.fixture
def contents_and_self():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Name>bucket</Name>
            <Prefix/>
            <Marker/>
            <MaxKeys>1000</MaxKeys>
            <IsTruncated>false</IsTruncated>
            <Contents>
                <Key>thisfolder/</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>0</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
            <Contents>
                <Key>thisfolder/item1</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>0</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
            <Contents>
                <Key>thisfolder/item2</Key>
                <LastModified>2009-10-12T17:50:30.000Z</LastModified>
                <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
                <Size>0</Size>
                <StorageClass>STANDARD</StorageClass>
                <Owner>
                    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                    <DisplayName>mtd@amazon.com</DisplayName>
                </Owner>
            </Contents>
        </ListBucketResult>'''


@pytest.fixture
def folder_empty_metadata():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Name>bucket</Name>
            <Prefix/>
            <Marker/>
            <MaxKeys>1000</MaxKeys>
            <IsTruncated>false</IsTruncated>
        </ListBucketResult>'''


@pytest.fixture
def file_metadata():
    return {
            'Content-Length': 9001,
            'Last-Modified': 'SomeTime',
            'Content-Type': 'binary/octet-stream',
            'ETag': '"fba9dede5f27731c9771645a39863328"'
    }


@pytest.fixture
def version_metadata():
    return b'''<?xml version="1.0" encoding="UTF-8"?>

    <ListVersionsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
        <Name>bucket</Name>
        <Prefix>my</Prefix>
        <KeyMarker/>
        <VersionIdMarker/>
        <MaxKeys>5</MaxKeys>
        <IsTruncated>false</IsTruncated>
        <Version>
            <Key>my-image.jpg</Key>
            <VersionId>3/L4kqtJl40Nr8X8gdRQBpUMLUo</VersionId>
            <IsLatest>true</IsLatest>
            <LastModified>2009-10-12T17:50:30.000Z</LastModified>
            <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
            <Size>434234</Size>
            <StorageClass>STANDARD</StorageClass>
            <Owner>
                <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                <DisplayName>mtd@amazon.com</DisplayName>
            </Owner>
        </Version>
        <Version>
            <Key>my-image.jpg</Key>
            <VersionId>QUpfdndhfd8438MNFDN93jdnJFkdmqnh893</VersionId>
            <IsLatest>false</IsLatest>
            <LastModified>2009-10-10T17:50:30.000Z</LastModified>
            <ETag>&quot;9b2cf535f27731c974343645a3985328&quot;</ETag>
            <Size>166434</Size>
            <StorageClass>STANDARD</StorageClass>
            <Owner>
                <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                <DisplayName>mtd@amazon.com</DisplayName>
            </Owner>
        </Version>
        <Version>
            <Key>my-image.jpg</Key>
            <VersionId>UIORUnfndfhnw89493jJFJ</VersionId>
            <IsLatest>false</IsLatest>
            <LastModified>2009-10-11T12:50:30.000Z</LastModified>
            <ETag>&quot;772cf535f27731c974343645a3985328&quot;</ETag>
            <Size>64</Size>
            <StorageClass>STANDARD</StorageClass>
            <Owner>
                <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
                <DisplayName>mtd@amazon.com</DisplayName>
            </Owner>
        </Version>
    </ListVersionsResult>'''


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider):
        path = S3Path('/muhtriangle')
        url = provider.bucket.new_key(path.path).generate_url(100, response_headers={'response-content-disposition': 'attachment'})
        aiohttpretty.register_uri('GET', url, body=b'delicious')

        result = yield from provider.download(str(path))
        content = yield from result.response.read()

        assert content == b'delicious'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider):
        path = S3Path('/muhtriangle')
        url = provider.bucket.new_key(path.path).generate_url(100, response_headers={'response-content-disposition': 'attachment'})
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_download_no_name(self, provider):
        with pytest.raises(ValueError):
            yield from provider.download('')
        with pytest.raises(exceptions.DownloadError):
            yield from provider.download('/')

    @async
    @pytest.mark.aiohttpretty
    def test_upload_update(self, provider, file_content, file_stream, file_metadata):
        path = S3Path('/foobah')
        content_md5 = hashlib.md5(file_content).hexdigest()
        url = provider.bucket.new_key(path.path).generate_url(100, 'PUT')
        metadata_url = provider.bucket.new_key(path.path).generate_url(100, 'HEAD')
        aiohttpretty.register_uri('HEAD', metadata_url, headers=file_metadata)
        aiohttpretty.register_uri('PUT', url, status=201, headers={'ETag': '"{}"'.format(content_md5)})

        metadata, created = yield from provider.upload(file_stream, str(path))

        assert metadata['kind'] == 'file'
        assert not created
        assert aiohttpretty.has_call(method='PUT', uri=url)
        assert aiohttpretty.has_call(method='HEAD', uri=metadata_url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete(self, provider):
        path = S3Path('/some-file')
        url = provider.bucket.new_key(path.path).generate_url(100, 'DELETE')
        aiohttpretty.register_uri('DELETE', url, status=200)

        yield from provider.delete(str(path))

        assert aiohttpretty.has_call(method='DELETE', uri=url)

    @async
    @pytest.mark.aiohttpretty
    def test_accepts_url(self, provider):
        path = S3Path('/my-image')
        url = provider.bucket.new_key(path.path).generate_url(100, 'GET', response_headers={'response-content-disposition': 'attachment'})

        ret_url = yield from provider.download(str(path), accept_url=True)

        assert ret_url == url


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder(self, provider, folder_metadata):
        path = S3Path('/darp/')
        url = provider.bucket.generate_url(100)
        aiohttpretty.register_uri('GET', url, body=folder_metadata, headers={'Content-Type': 'application/xml'})

        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[1]['name'] == 'my-image.jpg'
        assert result[2]['extra']['md5'] == '1b2cf535f27731c974343645a3985328'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_self_listing(self, provider, contents_and_self):
        path = S3Path('/thisfolder/')
        url = provider.bucket.generate_url(100)
        aiohttpretty.register_uri('GET', url, body=contents_and_self)

        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 2
        for fobj in result:
            assert fobj['name'] != path.path

    @async
    @pytest.mark.aiohttpretty
    def test_just_a_folder_metadata_folder(self, provider, just_a_folder_metadata):
        path = S3Path('/')
        url = provider.bucket.generate_url(100)
        aiohttpretty.register_uri('GET', url, body=just_a_folder_metadata, headers={'Content-Type': 'application/xml'})

        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['kind'] == 'folder'

    @async
    @pytest.mark.aiohttpretty
    def test_must_have_slash(self, provider, just_a_folder_metadata):
        with pytest.raises(ValueError):
            yield from provider.metadata('')

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file(self, provider, file_metadata):
        path = S3Path('/Foo/Bar/my-image.jpg')
        url = provider.bucket.new_key(path.path).generate_url(100, 'HEAD')
        aiohttpretty.register_uri('HEAD', url, headers=file_metadata)

        result = yield from provider.metadata(str(path))

        assert isinstance(result, dict)
        assert result['path'] == str(path)
        assert result['name'] == 'my-image.jpg'
        assert result['extra']['md5'] == 'fba9dede5f27731c9771645a39863328'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_missing(self, provider):
        path = S3Path('/notfound.txt')
        url = provider.bucket.new_key(path.path).generate_url(100, 'HEAD')
        aiohttpretty.register_uri('HEAD', url, status=404)

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_upload(self, provider, file_content, file_stream, file_metadata):
        path = S3Path('/foobah')
        content_md5 = hashlib.md5(file_content).hexdigest()
        url = provider.bucket.new_key(path.path).generate_url(100, 'PUT')
        metadata_url = provider.bucket.new_key(path.path).generate_url(100, 'HEAD')
        aiohttpretty.register_uri(
            'HEAD',
            metadata_url,
            responses=[
                {'status': 404},
                {'headers': file_metadata},
            ],
        )
        aiohttpretty.register_uri('PUT', url, status=200, headers={'ETag': '"{}"'.format(content_md5)}),

        metadata, created = yield from provider.upload(file_stream, str(path))

        assert metadata['kind'] == 'file'
        assert created
        assert aiohttpretty.has_call(method='PUT', uri=url)
        assert aiohttpretty.has_call(method='HEAD', uri=metadata_url)


class TestOperations:

    @async
    @pytest.mark.aiohttpretty
    def test_copy(self, provider, file_metadata):
        dest_path = S3Path('/dest')
        source_path = S3Path('/source')
        headers = {'x-amz-copy-source': '/{}/{}'.format(provider.settings['bucket'], source_path.path)}

        metadata_url = provider.bucket.new_key(dest_path.path).generate_url(100, 'HEAD')
        url = provider.bucket.new_key(dest_path.path).generate_url(100, 'PUT', headers=headers)

        aiohttpretty.register_uri('PUT', url, status=200)
        aiohttpretty.register_uri('HEAD', metadata_url, headers=file_metadata)

        resp = yield from provider.copy(provider, {'path': str(source_path)}, {'path': str(dest_path)})

        # TODO: matching url content for request
        assert resp['kind'] == 'file'
        assert aiohttpretty.has_call(method='HEAD', uri=metadata_url)
        assert aiohttpretty.has_call(method='PUT', uri=url, headers=headers)

    @async
    @pytest.mark.aiohttpretty
    def test_version_metadata(self, provider, version_metadata):
        path = S3Path('/my-image')
        url = provider.bucket.generate_url(100, 'GET', query_parameters={'versions': ''})
        aiohttpretty.register_uri('GET', url, status=200, body=version_metadata)

        data = yield from provider.revisions(str(path))

        assert isinstance(data, list)
        assert len(data) == 3

        for item in data:
            assert 'size' in item
            assert 'extra' in item
            assert 'revision' in item

        assert aiohttpretty.has_call(method='GET', uri=url)

    def test_equality(self, provider):
        assert provider.can_intra_copy(provider)
        assert provider.can_intra_move(provider)
