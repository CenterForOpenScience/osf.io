import pytest

from tests.utils import async

import io

import aiohttpretty

from waterbutler.core import exceptions

from waterbutler.providers.googledrive import GoogleDriveProvider
from waterbutler.providers.googledrive.metadata import GoogleDriveFileMetadata

from tests.providers.googledrive import fixtures


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {'token': 'hugoandkim'}


@pytest.fixture
def settings():
    return {
        'folder': {
            'id': '19003e',
            'name': '/conrad/birdie',
        },
    }


@pytest.fixture
def provider(auth, credentials, settings):
    return GoogleDriveProvider(auth, credentials, settings)


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download_drive(self, provider):
        path = '/birdie.jpg'
        body = b'we love you conrad'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        download_file_url = item['downloadUrl']
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_uri('GET', download_file_url, body=body)
        result = yield from provider.download(path)
        content = yield from result.response.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_download_drive_revision(self, provider):
        path = '/birdie.jpg'
        revision = 'oldest'
        body = b'we love you conrad'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        revision_url = provider.build_url('files', item['id'], 'revisions', revision)
        download_file_url = item['downloadUrl']
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_json_uri('GET', revision_url, body=item)
        aiohttpretty.register_uri('GET', download_file_url, body=body)
        result = yield from provider.download(path)
        content = yield from result.response.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_download_docs(self, provider):
        path = '/birdie.jpg'
        body = b'we love you conrad'
        item = fixtures.docs_file_metadata
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        revisions_url = provider.build_url('files', item['id'], 'revisions')
        download_file_url = item['exportLinks']['application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        aiohttpretty.register_json_uri('GET', list_file_url, body={'items': [item]})
        aiohttpretty.register_json_uri('GET', revisions_url, body={'items': [{'id': 'foo'}]})
        aiohttpretty.register_uri('GET', download_file_url, body=body)
        result = yield from provider.download(path)
        content = yield from result.response.read()
        assert content == body

    # @async
    # @pytest.mark.aiohttpretty
    # def test_upload_create(self, provider):
    #     pass

    # @async
    # @pytest.mark.aiohttpretty
    # def test_upload_update(self, provider):
    #     pass

    # @async
    # @pytest.mark.aiohttpretty
    # def test_delete(self, provider):
    #     pass


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_root(self, provider):
        path = '/birdie.jpg'
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        result = yield from provider.metadata(path)
        expected = GoogleDriveFileMetadata(fixtures.list_file['items'][0], '/').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_root_not_found(self, provider):
        path = '/birdie.jpg'
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file_empty)
        with pytest.raises(exceptions.MetadataError) as exc_info:
            yield from provider.metadata(path)
        assert exc_info.value.code == 404

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_nested(self, provider):
        path = '/ed/sullivan/show.mp3'
        parts = path.split('/')
        urls, bodies = [], []
        for idx, part in enumerate(parts[:-1]):
            query = provider._build_query(idx or provider.folder['id'], title=parts[idx + 1])
            body = fixtures.generate_list(idx + 1)
            url = provider.build_url('files', q=query, alt='json')
            aiohttpretty.register_json_uri('GET', url, body=body)
            urls.append(url)
            bodies.append(body)
        result = yield from provider.metadata(path)
        for url in urls:
            assert aiohttpretty.has_call(method='GET', uri=url)
        expected = GoogleDriveFileMetadata(bodies[-1]['items'][0], '/ed/sullivan').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file_nested_not_child(self, provider):
        path = '/ed/sullivan/show.mp3'
        query = provider._build_query(provider.folder['id'], title='ed')
        url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', url, body={'items': []})
        with pytest.raises(exceptions.MetadataError) as exc_info:
            yield from provider.metadata(path)
        assert exc_info.value.code == 404

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_root_folder(self, provider):
        path = '/'
        query = provider._build_query(provider.folder['id'])
        list_file_url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        result = yield from provider.metadata(path)
        expected = GoogleDriveFileMetadata(fixtures.list_file['items'][0], '/').serialized()
        assert result == [expected]

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_nested(self, provider):
        path = '/hugo/kim/pins/'
        parts = path.split('/')
        urls, bodies = [], []
        for idx, part in enumerate(parts[:-1]):
            query = provider._build_query(idx or provider.folder['id'], title=parts[idx + 1])
            body = fixtures.generate_list(idx + 1)
            url = provider.build_url('files', q=query, alt='json')
            aiohttpretty.register_json_uri('GET', url, body=body)
            urls.append(url)
            bodies.append(body)
        result = yield from provider.metadata(path)
        for url in urls:
            assert aiohttpretty.has_call(method='GET', uri=url)
        expected = GoogleDriveFileMetadata(bodies[-1]['items'][0], '/hugo/kim/pins').serialized()
        assert result == [expected]
