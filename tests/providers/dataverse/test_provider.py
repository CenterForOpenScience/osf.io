import pytest

from tests.utils import async

import io
import json

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings as dvs
from waterbutler.providers.dataverse import DataverseProvider
from waterbutler.providers.dataverse.metadata import DataverseFileMetadata


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
    return {
        'host': 'myfakehost.dataverse.org',
        'doi': 'doi:10.5072/FK2/ABCDEF',
        'id': '18',
        'name': 'A look at wizards',
    }


@pytest.fixture
def provider(auth, credentials, settings):
    return DataverseProvider(auth, credentials, settings)


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
def native_file_metadata():
    return   {'datafile': {'contentType': 'text/plain; charset=US-ASCII',
    'description': '',
    'filename': '%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73d734-8383551cc713',
    'id': 20,
    'md5': 'acbd18db4cc2f85cedef654fccc4a4d8',
    'name': 'thefile.txt',
    'originalFormatLabel': 'UNKNOWN'},
   'datasetVersionId': 5,
   'description': '',
   'label': 'thefile.txt',
   'version': 1}


@pytest.fixture
def native_dataset_metadata():
    return {'data': {'createTime': '2015-04-02T13:21:59Z',
 'distributionDate': 'Distribution Date',
 'files': [{'datafile': {'contentType': 'text/plain; charset=US-ASCII',
    'description': '',
    'filename': '%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73c684-4b22a1757aed',
    'id': 19,
    'md5': '2243b9249ca96f7cca9f58f7584b5ddb',
    'name': 'UnZip.java',
    'originalFormatLabel': 'UNKNOWN'},
   'datasetVersionId': 5,
   'description': '',
   'label': 'UnZip.java',
   'version': 1},
  {'datafile': {'contentType': 'text/plain; charset=US-ASCII',
    'description': '',
    'filename': '%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73d734-8383551cc713',
    'id': 20,
    'md5': 'acbd18db4cc2f85cedef654fccc4a4d8',
    'name': 'thefile.txt',
    'originalFormatLabel': 'UNKNOWN'},
   'datasetVersionId': 5,
   'description': '',
   'label': 'thefile.txt',
   'version': 1},
  {'datafile': {'contentType': 'application/octet-stream',
    'description': '',
    'filename': '%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73e419-b578b719b05c',
    'id': 21,
    'md5': 'ee5a34fe861617916acde862d4206280',
    'name': 'UnZip.class',
    'originalFormatLabel': 'UNKNOWN'},
   'datasetVersionId': 5,
   'description': '',
   'label': 'UnZip.class',
   'version': 1}],
 'id': 5,
 'lastUpdateTime': '2015-04-02T15:26:21Z',
 'metadataBlocks': {'citation': {'displayName': 'Citation Metadata',
   'fields': [{'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'title',
     'value': 'A look at wizards'},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'author',
     'value': [{'authorName': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'authorName',
        'value': 'Baggins, Bilbo'}}]},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'datasetContact',
     'value': [{'datasetContactEmail': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'datasetContactEmail',
        'value': 'email@email.com'},
       'datasetContactName': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'datasetContactName',
        'value': 'Baggins, Bilbo'}}]},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'dsDescription',
     'value': [{'dsDescriptionValue': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'dsDescriptionValue',
        'value': 'desc'}}]},
    {'multiple': True,
     'typeClass': 'controlledVocabulary',
     'typeName': 'subject',
     'value': ['Other']},
    {'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'depositor',
     'value': 'Baggins, Bilbo'},
    {'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'dateOfDeposit',
     'value': '2015-04-02'}]}},
 'productionDate': 'Production Date',
 'releaseTime': '2015-04-02T15:26:21Z',
 'versionMinorNumber': 0,
 'versionNumber': 1,
 'versionState': 'RELEASED'}}


@pytest.fixture
def empty_native_dataset_metadata():
    return {'data': {'createTime': '2015-04-02T13:21:59Z',
 'distributionDate': 'Distribution Date',
 'files': [],
 'id': 5,
 'lastUpdateTime': '2015-04-02T15:26:21Z',
 'metadataBlocks': {'citation': {'displayName': 'Citation Metadata',
   'fields': [{'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'title',
     'value': 'A look at wizards'},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'author',
     'value': [{'authorName': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'authorName',
        'value': 'Baggins, Bilbo'}}]},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'datasetContact',
     'value': [{'datasetContactEmail': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'datasetContactEmail',
        'value': 'email@email.com'},
       'datasetContactName': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'datasetContactName',
        'value': 'Baggins, Bilbo'}}]},
    {'multiple': True,
     'typeClass': 'compound',
     'typeName': 'dsDescription',
     'value': [{'dsDescriptionValue': {'multiple': False,
        'typeClass': 'primitive',
        'typeName': 'dsDescriptionValue',
        'value': 'desc'}}]},
    {'multiple': True,
     'typeClass': 'controlledVocabulary',
     'typeName': 'subject',
     'value': ['Other']},
    {'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'depositor',
     'value': 'Baggins, Bilbo'},
    {'multiple': False,
     'typeClass': 'primitive',
     'typeName': 'dateOfDeposit',
     'value': '2015-04-02'}]}},
 'productionDate': 'Production Date',
 'releaseTime': '2015-04-02T15:26:21Z',
 'versionMinorNumber': 0,
 'versionNumber': 1,
 'versionState': 'RELEASED'}}


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider, native_dataset_metadata):
        path = '/21'
        url = provider.build_url(dvs.DOWN_BASE_URL, path, key=provider.token)
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)

        aiohttpretty.register_uri('GET', url, body=b'better', auto_length=True)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path(path)

        result = yield from provider.download(path)
        content = yield from result.read()

        assert content == b'better'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider, native_dataset_metadata):
        path = '/21'
        url = provider.build_url(dvs.DOWN_BASE_URL, path, key=provider.token)
        aiohttpretty.register_uri('GET', url, status=404)
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path(path)

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(path)

    @async
    @pytest.mark.aiohttpretty
    def test_download_invalid_path(self, provider, native_dataset_metadata):
        path = '/50'
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path(path)

        with pytest.raises(exceptions.NotFoundError):
            yield from provider.download(path)

    @async
    @pytest.mark.aiohttpretty
    def test_upload_create(self, provider, file_stream, native_file_metadata, empty_native_dataset_metadata, native_dataset_metadata):
        path = '/thefile.txt'
        url = provider.build_url(dvs.EDIT_MEDIA_BASE_URL, 'study', provider.doi)
        aiohttpretty.register_uri('POST', url, status=201)
        latest_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        latest_published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)

        aiohttpretty.register_json_uri('GET', latest_published_url, body={'data': {'files': []}})
        aiohttpretty.register_uri('GET', latest_url, responses=[
            {
                'status': 200,
                'body': json.dumps(empty_native_dataset_metadata).encode('utf-8'),
                'headers': {'Content-Type': 'application/json'},
            },
            {
                'status': 200,
                'body': json.dumps(native_dataset_metadata).encode('utf-8'),
                'headers': {'Content-Type': 'application/json'},
            },
        ])

        path = yield from provider.validate_path(path)
        metadata, created = yield from provider.upload(file_stream, path)

        entry = native_file_metadata['datafile']
        expected = DataverseFileMetadata(entry, 'latest').serialized()

        assert created is True
        assert metadata == expected
        assert aiohttpretty.has_call(method='POST', uri=url)
        assert aiohttpretty.has_call(method='GET', uri=latest_url)
        assert aiohttpretty.has_call(method='GET', uri=latest_published_url)

    @async
    @pytest.mark.aiohttpretty
    def test_upload_updates(self, provider, file_stream, native_file_metadata, native_dataset_metadata):
        path = '/20'
        url = provider.build_url(dvs.EDIT_MEDIA_BASE_URL, 'study', provider.doi)
        aiohttpretty.register_uri('POST', url, status=201)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)
        delete_url = provider.build_url(dvs.EDIT_MEDIA_BASE_URL, 'file', '/20')  # Old file id
        aiohttpretty.register_json_uri('DELETE', delete_url, status=204)
        latest_published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)

        aiohttpretty.register_json_uri('GET', latest_published_url, body={'data': {'files': []}})

        path = yield from provider.validate_path(path)
        metadata, created = yield from provider.upload(file_stream, path)

        entry = native_file_metadata['datafile']
        expected = DataverseFileMetadata(entry, 'latest').serialized()

        assert metadata == expected
        assert created is False
        assert aiohttpretty.has_call(method='POST', uri=url)
        assert aiohttpretty.has_call(method='GET', uri=published_url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete_file(self, provider, native_dataset_metadata):
        path = '21'
        url = provider.build_url(dvs.EDIT_MEDIA_BASE_URL, 'file', path)
        aiohttpretty.register_json_uri('DELETE', url, status=204)
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path(path)
        yield from provider.delete(path)

        assert aiohttpretty.has_call(method='DELETE', uri=url)

    # @async
    # @pytest.mark.aiohttpretty
    # def test_delete_file_invalid_path(self, provider, native_dataset_metadata):
    #     path = '500'
    #     draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
    #     aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
    #     published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
    #     aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

    #     with pytest.raises(exceptions.MetadataError):
    #         yield from provider.delete(path)


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata(self, provider, native_dataset_metadata):
        url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path, version='latest')

        assert len(result) == 3
        assert result[0]['provider'] == 'dataverse'
        assert result[0]['kind'] == 'file'
        assert result[0]['name'] == 'UnZip.java'
        assert result[0]['path'] == '/19'
        assert result[0]['extra']['fileId'] == '19'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_no_files(self, provider, empty_native_dataset_metadata):
        url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', url, status=200, body=empty_native_dataset_metadata)
        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path, version='latest')

        assert result == []

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_published(self, provider, native_dataset_metadata):
        url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path, version='latest-published')

        assert len(result) == 3
        assert result[0]['provider'] == 'dataverse'
        assert result[0]['kind'] == 'file'
        assert result[0]['name'] == 'UnZip.java'
        assert result[0]['path'] == '/19'
        assert result[0]['extra']['fileId'] == '19'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_published_no_files(self, provider, empty_native_dataset_metadata):
        url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', url, status=200, body=empty_native_dataset_metadata)

        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path, version='latest-published')

        assert result == []

    @async
    @pytest.mark.aiohttpretty
    def test_draft_metadata_missing(self, provider):
        url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', url, status=404)

        path = yield from provider.validate_path('/')

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(path, version='latest')

    @async
    @pytest.mark.aiohttpretty
    def test_draft_metadata_no_state_catches_all(self, provider, native_dataset_metadata):
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path)

        assert isinstance(result, list)
        assert len(result) == 6

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_never_published(self, provider, native_dataset_metadata):
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=404)
        draft_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest'), key=provider.token)
        aiohttpretty.register_json_uri('GET', draft_url, status=200, body=native_dataset_metadata)

        path = yield from provider.validate_path('/')
        result = yield from provider.metadata(path)

        assert len(result) == 3

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_never_published_raises_errors(self, provider, native_dataset_metadata):
        published_url = provider.build_url(dvs.JSON_BASE_URL.format(provider._id, 'latest-published'), key=provider.token)
        aiohttpretty.register_json_uri('GET', published_url, status=400)

        with pytest.raises(exceptions.MetadataError):
            result = yield from provider.metadata(path='/')
