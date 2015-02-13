import pytest

from tests.utils import async

import io

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.box import BoxProvider
from waterbutler.providers.box.provider import BoxPath
from waterbutler.providers.box.metadata import BoxFileMetadata


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
    return {'folder': '/1234567890'}


@pytest.fixture
def provider(auth, credentials, settings):
    return BoxProvider(auth, credentials, settings)


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
def folder_metadata():
    return {
        "total_count": 24,
        "entries": [
            {
                "type": "folder",
                "id": "192429928",
                "sequence_id": "1",
                "etag": "1",
                "name": "Stephen Curry Three Pointers"
            },
            {
                "type": "file",
                "id": "818853862",
                "sequence_id": "0",
                "etag": "0",
                "name": "Warriors.jpg"
            }
        ],
        "offset": 0,
        "limit": 2,
        "order": [
            {
                "by": "type",
                "direction": "ASC"
            },
            {
                "by": "name",
                "direction": "ASC"
            }
        ]
    }


@pytest.fixture
def file_metadata():
    return {
        "type": "file",
        "id": "5000948880",
        "sequence_id": "3",
        "etag": "3",
        "sha1": "134b65991ed521fcfe4724b7d814ab8ded5185dc",
        "name": "tigers.jpeg",
        "description": "a picture of tigers",
        "size": 629644,
        "path_collection": {
            "total_count": 2,
            "entries": [
                {
                    "type": "folder",
                    "id": "0",
                    "sequence_id": null,
                    "etag": null,
                    "name": "All Files"
                },
                {
                    "type": "folder",
                    "id": "11446498",
                    "sequence_id": "1",
                    "etag": "1",
                    "name": "Pictures"
                }
            ]
        },
        "created_at": "2012-12-12T10:55:30-08:00",
        "modified_at": "2012-12-12T11:04:26-08:00",
        "created_by": {
            "type": "user",
            "id": "17738362",
            "name": "sean rose",
            "login": "sean@box.com"
        },
        "modified_by": {
            "type": "user",
            "id": "17738362",
            "name": "sean rose",
            "login": "sean@box.com"
        },
        "owned_by": {
            "type": "user",
            "id": "17738362",
            "name": "sean rose",
            "login": "sean@box.com"
        },
        "shared_link": {
            "url": "https://www.box.com/s/rh935iit6ewrmw0unyul",
            "download_url": "https://www.box.com/shared/static/rh935iit6ewrmw0unyul.jpeg",
            "vanity_url": null,
            "is_password_enabled": false,
            "unshared_at": null,
            "download_count": 0,
            "preview_count": 0,
            "access": "open",
            "permissions": {
                "can_download": true,
                "can_preview": true
            }
        },
        "parent": {
            "type": "folder",
            "id": "11446498",
            "sequence_id": "1",
            "etag": "1",
            "name": "Pictures"
        },
        "item_status": "active"
    }


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider):
        path = BoxPath(provider.folder + '/triangles.txt')
        url = provider._build_url('files', path._id, 'content')
        aiohttpretty.register_uri('GET', url, body=b'better')
        result = yield from provider.download(str(path))
        content = yield from result.response.read()

        assert content == b'better'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider):
        path = BoxPath(provider.folder + '/vectors.txt')
        url = provider._build_url('files', path._id, 'content')
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_upload(self, provider, file_metadata, file_stream, settings):
        path = BoxPath(provider.folder + '/phile')
        url = provider._build_upload_url('files', 'content')
        metadata_url = provider.build_url('folders', uid, 'items')
        aiohttpretty.register_uri('GET', metadata_url, status=404)
        aiohttpretty.register_json_uri('PUT', url, status=200, body=file_metadata)
        metadata, created = yield from provider.upload(file_stream, str(path))
        expected = BoxFileMetadata(file_metadata, provider.folder).serialized()

        assert metadata == expected
        assert created == True
        assert aiohttpretty.has_call(method='PUT', uri=url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete_file(self, provider, file_metadata):
        path = BoxPath(provider.folder +'/ThePast')
        url = provider.build_url('files', path._id)
        data = {'root': 'auto', 'path': path}
        file_url = provider.build_url('files', path._id, 'content')
        aiohttpretty.register_json_uri('GET', file_url, body=file_metadata)
        aiohttpretty.register_uri('POST', url, status=200)
        yield from provider.delete(str(path))

        assert aiohttpretty.has_call(method='GET', uri=file_url)
        assert aiohttpretty.has_call(method='POST', uri=url, data=data)


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata(self, provider, folder_metadata):
        path = BoxPath(provider.folder + '/')
        url = provider.build_url('folders', provide.folder, 'items')
        aiohttpretty.register_json_uri('GET', url, body=folder_metadata)
        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result['type'] == 'file'
        assert result['name'] == 'Warriors.jpg'
        assert result['path'] == '/818853862/Warriors.jpg'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_root_file(self, provider, file_metadata):
        path = BoxPath(provider.folder + '/pfile')
        url = provider.build_url('folders', provide.folder, 'items')
        aiohttpretty.register_json_uri('GET', url, body=file_metadata)
        result = yield from provider.metadata(str(path))

        assert isinstance(result, dict)
        assert result['type'] == 'file'
        assert result['name'] == 'Getting_Started.pdf'
        assert result['path'] == '/11446498/Getting_Started.pdf'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_missing(self, provider):
        path = BoxPath(provider.folder, '/pfile')
        url = provider.build_url('metadata', 'auto', path.full_path)
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(str(path))


class TestOperations:

    def test_can_intra_copy(self, provider):
        assert provider.can_intra_copy(provider)

    def test_can_intra_move(self, provider):
        assert provider.can_intra_move(provider)
