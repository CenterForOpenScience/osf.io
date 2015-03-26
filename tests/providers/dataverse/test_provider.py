import pytest

from tests.utils import async

import io

import aiohttpretty
import xmltodict

from waterbutler.core import streams
from waterbutler.core import exceptions
from waterbutler.core.provider import build_url

from waterbutler.providers.dataverse import DataverseProvider, settings, utils
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
    return {'doi': 'doi:10.5072/FK2/ABCDEF'}


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


# @pytest.fixture
# def folder_metadata():
#     return {
#         "size": "0 bytes",
#         "hash": "37eb1ba1849d4b0fb0b28caf7ef3af52",
#         "bytes": 0,
#         "thumb_exists": False,
#         "rev": "714f029684fe",
#         "modified": "Wed, 27 Apr 2011 22:18:51 +0000",
#         "path": "/Photos",
#         "is_dir": True,
#         "icon": "folder",
#         "root": "dropbox",
#         "contents": [
#             {
#                 "size": "2.3 MB",
#                 "rev": "38af1b183490",
#                 "thumb_exists": True,
#                 "bytes": 2453963,
#                 "modified": "Mon, 07 Apr 2014 23:13:16 +0000",
#                 "client_mtime": "Thu, 29 Aug 2013 01:12:02 +0000",
#                 "path": "/Photos/flower.jpg",
#                 "photo_info": {
#                 "lat_long": [
#                     37.77256666666666,
#                     -122.45934166666667
#                 ],
#                 "time_taken": "Wed, 28 Aug 2013 18:12:02 +0000"
#                 },
#                 "is_dir": False,
#                 "icon": "page_white_picture",
#                 "root": "dropbox",
#                 "mime_type": "image/jpeg",
#                 "revision": 14511
#             }
#         ],
#         "revision": 29007
#     }
#

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
        expected = DataverseFileMetadata(entry).serialized()

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


# class TestMetadata:
#
#     @async
#     @pytest.mark.aiohttpretty
#     def test_metadata(self, provider, folder_metadata):
#         path = DropboxPath(provider.folder, '/')
#         url = provider.build_url('metadata', 'auto', path.full_path)
#         aiohttpretty.register_json_uri('GET', url, body=folder_metadata)
#         result = yield from provider.metadata(str(path))
#
#         assert isinstance(result, list)
#         assert len(result) == 1
#         assert result[0]['kind'] == 'file'
#         assert result[0]['name'] == 'flower.jpg'
#         assert result[0]['path'] == '/flower.jpg'
#
#     @async
#     @pytest.mark.aiohttpretty
#     def test_metadata_root_file(self, provider, file_metadata):
#         path = DropboxPath(provider.folder, '/pfile')
#         url = provider.build_url('metadata', 'auto', path.full_path)
#         aiohttpretty.register_json_uri('GET', url, body=file_metadata)
#         result = yield from provider.metadata(str(path))
#
#         assert isinstance(result, dict)
#         assert result['kind'] == 'file'
#         assert result['name'] == 'Getting_Started.pdf'
#         assert result['path'] == '/Getting_Started.pdf'
#
#     @async
#     @pytest.mark.aiohttpretty
#     def test_metadata_missing(self, provider):
#         path = DropboxPath(provider.folder, '/pfile')
#         url = provider.build_url('metadata', 'auto', path.full_path)
#         aiohttpretty.register_uri('GET', url, status=404)
#
#         with pytest.raises(exceptions.MetadataError):
#             yield from provider.metadata(str(path))
#
#
# class TestOperations:
#
#     def test_can_intra_copy(self, provider):
#         assert provider.can_intra_copy(provider)
#
#     def test_can_intra_move(self, provider):
#         assert provider.can_intra_move(provider)
