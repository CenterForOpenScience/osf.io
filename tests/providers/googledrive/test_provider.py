import pytest

from tests.utils import async

import io

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.googledrive import settings as ds
from waterbutler.providers.googledrive import GoogleDriveProvider
from waterbutler.providers.googledrive.metadata import GoogleDriveRevision
from waterbutler.providers.googledrive.metadata import GoogleDriveFileMetadata

from tests.providers.googledrive import fixtures


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
        path = '/birdie\'"".jpg'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        assert 'birdie\\\'\\"\\".jpg' in query

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
        revision_url = provider.build_url('files', item['id'], 'revisions', revision, alt='json')
        download_file_url = item['downloadUrl']
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_json_uri('GET', revision_url, body=item)
        aiohttpretty.register_uri('GET', download_file_url, body=body)
        result = yield from provider.download(path, revision=revision)
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

    @async
    @pytest.mark.aiohttpretty
    def test_upload_create(self, provider, file_stream):
        path = '/birdie.jpg'
        upload_id = '7'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        start_upload_url = provider._build_upload_url('files', uploadType='resumable')
        finish_upload_url = provider._build_upload_url('files', uploadType='resumable', upload_id=upload_id)
        aiohttpretty.register_json_uri('GET', list_file_url, body={'items': []})
        aiohttpretty.register_uri('POST', start_upload_url, headers={'LOCATION': 'http://waterbutler.io?upload_id={}'.format(upload_id)})
        aiohttpretty.register_json_uri('PUT', finish_upload_url, body=item)
        result, created = yield from provider.upload(file_stream, path)

        assert aiohttpretty.has_call(method='GET', uri=list_file_url)
        assert aiohttpretty.has_call(method='POST', uri=start_upload_url)
        assert aiohttpretty.has_call(method='PUT', uri=finish_upload_url)
        assert created is True
        expected = GoogleDriveFileMetadata(item, '/').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_upload_doesnt_unquote(self, provider, file_stream):
        path = '/birdie%2F %20".jpg'
        upload_id = '7'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        start_upload_url = provider._build_upload_url('files', uploadType='resumable')
        finish_upload_url = provider._build_upload_url('files', uploadType='resumable', upload_id=upload_id)
        aiohttpretty.register_json_uri('GET', list_file_url, body={'items': []})
        aiohttpretty.register_uri('POST', start_upload_url, headers={'LOCATION': 'http://waterbutler.io?upload_id={}'.format(upload_id)})
        aiohttpretty.register_json_uri('PUT', finish_upload_url, body=item)
        result, created = yield from provider.upload(file_stream, path)

        assert aiohttpretty.has_call(method='GET', uri=list_file_url)
        assert aiohttpretty.has_call(method='POST', uri=start_upload_url)
        assert aiohttpretty.has_call(method='PUT', uri=finish_upload_url)
        assert created is True
        expected = GoogleDriveFileMetadata(item, '/').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_upload_update(self, provider, file_stream):
        path = '/birdie.jpg'
        upload_id = '7'
        item = fixtures.list_file['items'][0]
        file_id = item['id']
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        start_upload_url = provider._build_upload_url('files', file_id, uploadType='resumable')
        finish_upload_url = provider._build_upload_url('files', file_id, uploadType='resumable', upload_id=upload_id)
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_uri('PUT', start_upload_url, headers={'LOCATION': 'http://waterbutler.io?upload_id={}'.format(upload_id)})
        aiohttpretty.register_json_uri('PUT', finish_upload_url, body=item)
        result, created = yield from provider.upload(file_stream, path)

        assert aiohttpretty.has_call(method='GET', uri=list_file_url)
        assert aiohttpretty.has_call(method='PUT', uri=start_upload_url)
        assert aiohttpretty.has_call(method='PUT', uri=finish_upload_url)
        assert created is False
        expected = GoogleDriveFileMetadata(item, '/').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_upload_create_nested(self, provider, file_stream):
        path = '/ed/sullivan/show.mp3'
        upload_id = '7'
        parts = path.split('/')
        urls, bodies = [], []
        for idx, part in enumerate(parts[:-1]):
            query = provider._build_query(idx or provider.folder['id'], title=parts[idx + 1])
            if part == 'sullivan':
                body = {'items': []}
            else:
                body = fixtures.generate_list(idx + 1)
            url = provider.build_url('files', q=query, alt='json')
            aiohttpretty.register_json_uri('GET', url, body=body)
            urls.append(url)
            bodies.append(body)
        item = fixtures.list_file['items'][0]
        start_upload_url = provider._build_upload_url('files', uploadType='resumable')
        finish_upload_url = provider._build_upload_url('files', uploadType='resumable', upload_id=upload_id)
        aiohttpretty.register_uri('POST', start_upload_url, headers={'LOCATION': 'http://waterbutler.io?upload_id={}'.format(upload_id)})
        aiohttpretty.register_json_uri('PUT', finish_upload_url, body=item)
        result, created = yield from provider.upload(file_stream, path)

        assert aiohttpretty.has_call(method='POST', uri=start_upload_url)
        assert aiohttpretty.has_call(method='PUT', uri=finish_upload_url)
        assert created is True
        expected = GoogleDriveFileMetadata(item, '/ed/sullivan').serialized()
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_delete(self, provider):
        path = '/birdie.jpg'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        delete_url = provider.build_url('files', item['id'])
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_uri('DELETE', delete_url, status=204)
        result = yield from provider.delete(path)

        assert aiohttpretty.has_call(method='GET', uri=list_file_url)
        assert aiohttpretty.has_call(method='DELETE', uri=delete_url)
        assert result is None

    @async
    @pytest.mark.aiohttpretty
    def test_delete_folder(self, provider):
        path = '/foobar/'
        item = fixtures.folder_metadata

        query = provider._build_query(provider.folder['id'], title='foobar')
        query2 = provider._build_query(item['id'])
        print(query2)
        list_file_url = provider.build_url('files', q=query, alt='json')
        list_file_url2 = provider.build_url('files', q=query2, alt='json')
        delete_url = provider.build_url('files', item['id'])

        aiohttpretty.register_json_uri('GET', list_file_url, body={
            'items': [item]
        })
        aiohttpretty.register_json_uri('GET', list_file_url2, body={
            'items': [item]
        })
        aiohttpretty.register_json_uri('GET', provider.build_url('files', item['id']), body=item)
        aiohttpretty.register_uri('DELETE', delete_url, status=204)

        result = yield from provider.delete(path)

        assert aiohttpretty.has_call(method='GET', uri=list_file_url)
        assert aiohttpretty.has_call(method='DELETE', uri=delete_url)


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


class TestRevisions:

    @async
    @pytest.mark.aiohttpretty
    def test_get_revisions(self, provider):
        path = '/birdie.jpg'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        revisions_url = provider.build_url('files', item['id'], 'revisions')
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_json_uri('GET', revisions_url, body=fixtures.revisions_list)
        result = yield from provider.revisions(path)
        expected = [
            GoogleDriveRevision(each).serialized()
            for each in fixtures.revisions_list['items']
        ]
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_get_revisions_no_revisions(self, provider, monkeypatch):
        path = '/birdie.jpg'
        item = fixtures.list_file['items'][0]
        query = provider._build_query(provider.folder['id'], title=path.lstrip('/'))
        list_file_url = provider.build_url('files', q=query, alt='json')
        revisions_url = provider.build_url('files', item['id'], 'revisions')
        aiohttpretty.register_json_uri('GET', list_file_url, body=fixtures.list_file)
        aiohttpretty.register_json_uri('GET', revisions_url, body=fixtures.revisions_list_empty)
        result = yield from provider.revisions(path)
        expected = [
            GoogleDriveRevision({
                'modifiedDate': item['modifiedDate'],
                'id': fixtures.revisions_list_empty['etag'] + ds.DRIVE_IGNORE_VERSION,
            }).serialized()
        ]
        assert result == expected


class TestCreateFolder:

    @async
    @pytest.mark.aiohttpretty
    def test_already_exists(self, provider):
        path = '/hugo/kim/pins/'
        parts = path.split('/')

        for idx, part in enumerate(parts[:-1]):
            query = provider._build_query(idx or provider.folder['id'], title=parts[idx + 1])
            body = fixtures.generate_list(idx + 1)
            url = provider.build_url('files', q=query, alt='json')
            aiohttpretty.register_json_uri('GET', url, body=body)

        with pytest.raises(exceptions.FolderNamingConflict) as e:
            yield from provider.create_folder(path)

        assert e.value.code == 409
        assert e.value.message == 'Cannot create folder "pins" because a file or folder already exists at path "/hugo/kim/pins/"'

    @async
    @pytest.mark.aiohttpretty
    def test_returns_metadata(self, provider):
        path = '/osf test/'

        query = provider._build_query(provider.folder['id'], title='osf test')
        url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', url, status=404)
        aiohttpretty.register_json_uri('POST', provider.build_url('files'), body=fixtures.folder_metadata)

        resp = yield from provider.create_folder(path)

        assert resp['kind'] == 'folder'
        assert resp['name'] == 'osf test'
        assert resp['path'] == '/osf%20test/'

    @async
    @pytest.mark.aiohttpretty
    def test_raises_non_404(self, provider):
        path = '/hugo/kim/pins/'
        parts = path.split('/')

        query = provider._build_query(provider.folder['id'], title=parts[1])
        url = provider.build_url('files', q=query, alt='json')
        aiohttpretty.register_json_uri('GET', url, status=418)

        with pytest.raises(exceptions.MetadataError) as e:
            yield from provider.create_folder(path)

        assert e.value.code == 418

    @async
    @pytest.mark.aiohttpretty
    def test_must_be_folder(self, provider, monkeypatch):
        with pytest.raises(exceptions.CreateFolderError) as e:
            yield from provider.create_folder('/carp.fish')
