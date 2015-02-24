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
    return {'folder': '11446498'}


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
def folder_object_metadata():
    return {
        "type": "folder",
        "id": "11446498",
        "sequence_id": "1",
        "etag": "1",
        "name": "Pictures",
        "created_at": "2012-12-12T10:53:43-08:00",
        "modified_at": "2012-12-12T11:15:04-08:00",
        "description": "Some pictures I took",
        "size": 629644,
        "path_collection": {
            "total_count": 1,
            "entries": [
                {
                    "type": "folder",
                    "id": "0",
                    "sequence_id": None,
                    "etag": None,
                    "name": "All Files"
                }
            ]
        },
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
            "url": "https://www.box.com/s/vspke7y05sb214wjokpk",
            "download_url": None,
            "vanity_url": None,
            "is_password_enabled": False,
            "unshared_at": None,
            "download_count": 0,
            "preview_count": 0,
            "access": "open",
            "permissions": {
                "can_download": True,
                "can_preview": True
            }
        },
        "folder_upload_email": {
            "access": "open",
            "email": "upload.Picture.k13sdz1@u.box.com"
        },
        "parent": {
            "type": "folder",
            "id": "0",
            "sequence_id": None,
            "etag": None,
            "name": "All Files"
        },
        "item_status": "active",
        "item_collection": {
            "total_count": 1,
            "entries": [
                {
                    "type": "file",
                    "id": "5000948880",
                    "sequence_id": "3",
                    "etag": "3",
                    "sha1": "134b65991ed521fcfe4724b7d814ab8ded5185dc",
                    "name": "tigers.jpeg"
                }
            ],
            "offset": 0,
            "limit": 100
        },
        "tags": [
            "approved",
            "ready to publish"
        ]
    }


@pytest.fixture
def folder_list_metadata():
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
    return {'entries': [{
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
                            "sequence_id": None,
                            "etag": None,
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
                    "vanity_url": None,
                    "is_password_enabled": False,
                    "unshared_at": None,
                    "download_count": 0,
                    "preview_count": 0,
                    "access": "open",
                    "permissions": {
                        "can_download": True,
                        "can_preview": True
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
            }]
        }



class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider):
        path = BoxPath('/' + provider.folder + '/triangles.txt')
        url = provider.build_url('files', path._id, 'content')
        aiohttpretty.register_uri('GET', url, body=b'better')
        result = yield from provider.download(str(path))
        content = yield from result.response.read()

        assert content == b'better'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider):
        path = BoxPath('/' + provider.folder + '/vectors.txt')
        url = provider.build_url('files', path._id, 'content')
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_upload(self, provider, file_metadata, file_stream, settings):
        path = BoxPath('/' + provider.folder + '/phile')
        url = provider._build_upload_url('files', 'content')
        metadata_folder_url = provider.build_url('folders', path._id, 'items')
        metadata_file_url = provider.build_url('files', path._id)
        aiohttpretty.register_uri('GET', metadata_folder_url, status=404)
        aiohttpretty.register_uri('GET', metadata_file_url, status=404)
        aiohttpretty.register_json_uri('POST', url, status=200, body=file_metadata)
        metadata, created = yield from provider.upload(file_stream, '/{}'.format(path.name))
        expected = BoxFileMetadata(file_metadata['entries'][0], provider.folder).serialized()

        assert metadata == expected
        assert created is True
        assert aiohttpretty.has_call(method='POST', uri=url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete_file(self, provider, file_metadata):
        path = BoxPath('/' + provider.folder + '/ThePast')
        url = provider.build_url('files', path._id)
        aiohttpretty.register_uri('DELETE', url, status=204)
        yield from provider.delete(str(path))

        assert aiohttpretty.has_call(method='DELETE', uri=url)


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata(self, provider, folder_object_metadata, folder_list_metadata):
        path = BoxPath('/' + provider.folder + '/')
        object_url = provider.build_url('folders', provider.folder)
        list_url = provider.build_url('folders', provider.folder, 'items')
        aiohttpretty.register_json_uri('GET', object_url, body=folder_object_metadata)
        aiohttpretty.register_json_uri('GET', list_url, body=folder_list_metadata)

        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[1]['kind'] == 'file'
        assert result[1]['name'] == 'Warriors.jpg'
        assert result[1]['path'] == '/818853862/Warriors.jpg'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_root_file(self, provider, file_metadata):
        path = BoxPath('/' + provider.folder + '/pfile')
        url = provider.build_url('files', path._id)
        aiohttpretty.register_json_uri('GET', url, body=file_metadata['entries'][0])
        result = yield from provider.metadata(str(path))

        assert isinstance(result, dict)
        assert result['kind'] == 'file'
        assert result['name'] == 'tigers.jpeg'
        assert result['path'] == '/5000948880/tigers.jpeg'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_missing(self, provider):
        path = BoxPath('/' + provider.folder + '/pfile')
        url = provider.build_url('files', path._id)
        aiohttpretty.register_uri('GET', url, status=404)

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(str(path))
