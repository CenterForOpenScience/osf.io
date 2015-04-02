import pytest

from tests.utils import async

import io

import aiohttpretty
import xmltodict

from waterbutler.core import streams
from waterbutler.core import exceptions
from waterbutler.core.provider import build_url

from waterbutler.providers.dataverse import DataverseProvider
from waterbutler.providers.dataverse.metadata import DataverseSwordFileMetadata


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
        'doi': 'doi:10.5072/FK2/ABCDEF',
        'id': '18',
        'name': 'A look at wizards'
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
def file_metadata():
    return b'''<entry>
            <content type="text/plain; charset=US-ASCII" src="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt"/>
            <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt</id>
            <title type="text">Resource https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt</title>
            <summary type="text">Resource Part</summary>
            <updated>2015-03-26T20:00:12.361Z</updated>
        </entry>'''


@pytest.fixture
def dataset_metadata():
    return b'''<feed xmlns="http://www.w3.org/2005/Atom">
        <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit/study/doi:10.5072/FK2/ABCDEF</id>
        <link href="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit/study/doi:10.5072/FK2/ABCDEF" rel="self"/>
        <title type="text">A look at wizards</title>
        <author>
            <name>Potter, Harry</name>
        </author>
        <updated>2015-03-26T18:53:50.917Z</updated>
        <entry>
            <content type="text/plain; charset=US-ASCII" src="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/161/thefile-2.txt"/>
            <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/161/thefile-2.txt</id>
            <title type="text">Resource https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/161/thefile-2.txt</title>
            <summary type="text">Resource Part</summary>
            <updated>2015-03-26T20:00:12.361Z</updated>
        </entry>
        <entry>
            <content type="text/plain; charset=US-ASCII" src="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt"/>
            <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt</id>
            <title type="text">Resource https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/162/thefile-3.txt</title>
            <summary type="text">Resource Part</summary>
            <updated>2015-03-26T20:00:12.361Z</updated>
        </entry>
        <entry>
            <content type="text/plain; charset=US-ASCII" src="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/150/thefile.txt"/>
            <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/150/thefile.txt</id>
            <title type="text">Resource https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/150/thefile.txt</title>
            <summary type="text">Resource Part</summary>
            <updated>2015-03-26T20:00:12.361Z</updated>
        </entry>
        <entry>
            <content type="text/plain; charset=US-ASCII" src="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/163/thefile-1.txt"/>
            <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/163/thefile-1.txt</id>
            <title type="text">Resource https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/163/thefile-1.txt</title>
            <summary type="text">Resource Part</summary>
            <updated>2015-03-26T20:00:12.361Z</updated>
        </entry>
        <category term="isMinorUpdate" scheme="http://purl.org/net/sword/terms/state" label="State">true</category>
        <category term="locked" scheme="http://purl.org/net/sword/terms/state" label="State">false</category>
        <category term="latestVersionState" scheme="http://purl.org/net/sword/terms/state" label="State">DRAFT</category>
    </feed>'''


@pytest.fixture
def empty_dataset_metadata():
    return b'''<feed xmlns="http://www.w3.org/2005/Atom">
        <id>https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit/study/doi:10.5072/FK2/ABCDEF</id>
        <link href="https://apitest.dataverse.org/dvn/api/data-deposit/v1.1/swordv2/edit/study/doi:10.5072/FK2/ABCDEF" rel="self"/>
        <title type="text">A look at wizards</title>
        <author>
            <name>Potter, Harry</name>
        </author>
        <updated>2015-03-26T18:53:50.917Z</updated>
        <category term="isMinorUpdate" scheme="http://purl.org/net/sword/terms/state" label="State">true</category>
        <category term="locked" scheme="http://purl.org/net/sword/terms/state" label="State">false</category>
        <category term="latestVersionState" scheme="http://purl.org/net/sword/terms/state" label="State">DRAFT</category>
    </feed>'''


@pytest.fixture
def native_dataset_metadata():
    return {'data': {u'createTime': u'2015-04-02T13:21:59Z',
 u'distributionDate': u'Distribution Date',
 u'files': [{u'datafile': {u'contentType': u'text/plain; charset=US-ASCII',
    u'description': u'',
    u'filename': u'%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73c684-4b22a1757aed',
    u'id': 19,
    u'md5': u'2243b9249ca96f7cca9f58f7584b5ddb',
    u'name': u'UnZip.java',
    u'originalFormatLabel': u'UNKNOWN'},
   u'datasetVersionId': 5,
   u'description': u'',
   u'label': u'UnZip.java',
   u'version': 1},
  {u'datafile': {u'contentType': u'text/plain; charset=US-ASCII',
    u'description': u'',
    u'filename': u'%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73d734-8383551cc713',
    u'id': 20,
    u'md5': u'acbd18db4cc2f85cedef654fccc4a4d8',
    u'name': u'thefile.txt',
    u'originalFormatLabel': u'UNKNOWN'},
   u'datasetVersionId': 5,
   u'description': u'',
   u'label': u'thefile.txt',
   u'version': 1},
  {u'datafile': {u'contentType': u'application/octet-stream',
    u'description': u'',
    u'filename': u'%2Fusr%2Flocal%2Fglassfish4%2Fglassfish%2Fdomains%2Fdomain1%2Ffiles%2F10.5072%2FFK2%2F232XYH%2F14c7a73e419-b578b719b05c',
    u'id': 21,
    u'md5': u'ee5a34fe861617916acde862d4206280',
    u'name': u'UnZip.class',
    u'originalFormatLabel': u'UNKNOWN'},
   u'datasetVersionId': 5,
   u'description': u'',
   u'label': u'UnZip.class',
   u'version': 1}],
 u'id': 5,
 u'lastUpdateTime': u'2015-04-02T15:26:21Z',
 u'metadataBlocks': {u'citation': {u'displayName': u'Citation Metadata',
   u'fields': [{u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'title',
     u'value': u'A look at wizards'},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'author',
     u'value': [{u'authorName': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'authorName',
        u'value': u'Baggins, Bilbo'}}]},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'datasetContact',
     u'value': [{u'datasetContactEmail': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'datasetContactEmail',
        u'value': u'email@email.com'},
       u'datasetContactName': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'datasetContactName',
        u'value': u'Baggins, Bilbo'}}]},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'dsDescription',
     u'value': [{u'dsDescriptionValue': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'dsDescriptionValue',
        u'value': u'desc'}}]},
    {u'multiple': True,
     u'typeClass': u'controlledVocabulary',
     u'typeName': u'subject',
     u'value': [u'Other']},
    {u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'depositor',
     u'value': u'Baggins, Bilbo'},
    {u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'dateOfDeposit',
     u'value': u'2015-04-02'}]}},
 u'productionDate': u'Production Date',
 u'releaseTime': u'2015-04-02T15:26:21Z',
 u'versionMinorNumber': 0,
 u'versionNumber': 1,
 u'versionState': u'RELEASED'}}


@pytest.fixture
def empty_native_dataset_metadata():
    return {'data': {u'createTime': u'2015-04-02T13:21:59Z',
 u'distributionDate': u'Distribution Date',
 u'files': [],
 u'id': 5,
 u'lastUpdateTime': u'2015-04-02T15:26:21Z',
 u'metadataBlocks': {u'citation': {u'displayName': u'Citation Metadata',
   u'fields': [{u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'title',
     u'value': u'A look at wizards'},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'author',
     u'value': [{u'authorName': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'authorName',
        u'value': u'Baggins, Bilbo'}}]},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'datasetContact',
     u'value': [{u'datasetContactEmail': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'datasetContactEmail',
        u'value': u'email@email.com'},
       u'datasetContactName': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'datasetContactName',
        u'value': u'Baggins, Bilbo'}}]},
    {u'multiple': True,
     u'typeClass': u'compound',
     u'typeName': u'dsDescription',
     u'value': [{u'dsDescriptionValue': {u'multiple': False,
        u'typeClass': u'primitive',
        u'typeName': u'dsDescriptionValue',
        u'value': u'desc'}}]},
    {u'multiple': True,
     u'typeClass': u'controlledVocabulary',
     u'typeName': u'subject',
     u'value': [u'Other']},
    {u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'depositor',
     u'value': u'Baggins, Bilbo'},
    {u'multiple': False,
     u'typeClass': u'primitive',
     u'typeName': u'dateOfDeposit',
     u'value': u'2015-04-02'}]}},
 u'productionDate': u'Production Date',
 u'releaseTime': u'2015-04-02T15:26:21Z',
 u'versionMinorNumber': 0,
 u'versionNumber': 1,
 u'versionState': u'RELEASED'}}


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider):
        path = '/triangles.txt'
        url = build_url(provider.DOWN_BASE_URL, path)
        aiohttpretty.register_uri('GET', url, body=b'better')
        result = yield from provider.download(str(path))
        content = yield from result.response.read()

        assert content == b'better'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider):
        path = '/triangles.txt'
        url = build_url(provider.DOWN_BASE_URL, path)
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(str(path))


    @async
    @pytest.mark.aiohttpretty
    def test_upload(self, provider, file_stream, file_metadata, dataset_metadata):
        path = '/thefile.txt'
        url = build_url(provider.EDIT_MEDIA_BASE_URL, 'study', provider.doi)
        metadata_url = build_url(provider.METADATA_BASE_URL, provider.doi)
        aiohttpretty.register_uri('POST', url, status=201)
        aiohttpretty.register_uri('GET', metadata_url, status=200, body=dataset_metadata)

        metadata, created = yield from provider.upload(file_stream, path)

        entry = xmltodict.parse(file_metadata)['entry']
        expected = DataverseSwordFileMetadata(entry).serialized()

        assert metadata == expected
        assert created is True
        assert aiohttpretty.has_call(method='POST', uri=url)
        assert aiohttpretty.has_call(method='GET', uri=metadata_url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete_file(self, provider):
        path = '/The past'
        url = build_url(provider.EDIT_MEDIA_BASE_URL, 'file', path)
        aiohttpretty.register_json_uri('DELETE', url, status=204)

        yield from provider.delete(str(path))

        assert aiohttpretty.has_call(method='DELETE', uri=url)


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata(self, provider, dataset_metadata):
        url = build_url(provider.METADATA_BASE_URL, provider.doi)
        aiohttpretty.register_uri('GET', url, status=200, body=dataset_metadata)

        result = yield from provider.metadata(state='draft')

        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0]['provider'] == 'dataverse'
        assert result[0]['kind'] == 'file'
        assert result[0]['name'] == 'thefile-2.txt'
        assert result[0]['path'] == '/161'
        assert result[0]['extra']['original'] == 'thefile.txt'
        assert result[0]['extra']['version'] == 2
        assert result[0]['extra']['fileId'] == '161'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_no_files(self, provider, empty_dataset_metadata):
        url = build_url(provider.METADATA_BASE_URL, provider.doi)
        aiohttpretty.register_uri('GET', url, status=200, body=empty_dataset_metadata)

        result = yield from provider.metadata(state='draft')

        assert isinstance(result, dict)
        assert result['provider'] == 'dataverse'
        assert result['kind'] == 'folder'
        assert result['name'] == 'A look at wizards'
        assert result['path'] == '/{0}/'.format(provider.doi)

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_published(self, provider, native_dataset_metadata):
        url = provider.JSON_BASE_URL.format(provider.id)
        aiohttpretty.register_json_uri('GET', url, status=200, body=native_dataset_metadata)

        result = yield from provider.metadata(state='published')

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]['provider'] == 'dataverse'
        assert result[0]['kind'] == 'file'
        assert result[0]['name'] == 'UnZip.java'
        assert result[0]['path'] == '/19'
        assert result[0]['extra']['original'] == 'UnZip.java'
        assert result[0]['extra']['version'] == 0
        assert result[0]['extra']['fileId'] == '19'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_published_no_files(self, provider, empty_native_dataset_metadata):
        url = provider.JSON_BASE_URL.format(provider.id)
        aiohttpretty.register_json_uri('GET', url, status=200, body=empty_native_dataset_metadata)

        result = yield from provider.metadata(state='published')

        assert isinstance(result, dict)
        assert result['provider'] == 'dataverse'
        assert result['kind'] == 'folder'
        assert result['name'] == 'A look at wizards'
        assert result['path'] == '/{0}/'.format(provider.doi)


    @async
    @pytest.mark.aiohttpretty
    def test_draft_metadata_missing(self, provider):
        url = build_url(provider.METADATA_BASE_URL, provider.doi)
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(state='draft')

    @async
    @pytest.mark.aiohttpretty
    def test_draft_metadata_no_state_catches_all(self, provider, dataset_metadata, native_dataset_metadata):
        sword_url = build_url(provider.METADATA_BASE_URL, provider.doi)
        aiohttpretty.register_uri('GET', sword_url, status=200, body=dataset_metadata)
        json_url = provider.JSON_BASE_URL.format(provider.id)
        aiohttpretty.register_json_uri('GET', json_url, status=200, body=native_dataset_metadata)

        result = yield from provider.metadata()

        assert isinstance(result, list)
        assert len(result) == 7