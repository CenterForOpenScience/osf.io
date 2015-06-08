import pytest

from tests.utils import async

import io

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions
from waterbutler.core.path import WaterButlerPath

from waterbutler.providers.box import BoxProvider
from waterbutler.providers.box.metadata import BoxRevision
from waterbutler.providers.box.metadata import BoxFileMetadata
from waterbutler.providers.box.metadata import BoxFolderMetadata


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
    return {
        'entries': [
            {
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
            }
        ]
    }


@pytest.fixture
def revisions_list_metadata():
    return {
        'entries': [
            {'name': 'lode.txt', 'modified_by': {'login': 'jmcarp@umich.edu', 'id': '183920511', 'type': 'user', 'name': 'Joshua Carp'}, 'modified_at': '2015-02-24T09:26:02-08:00', 'size': 1620, 'id': '25065971851', 'sha1': 'f313795ea4184ddbb7d12d3691d1850b83fe9b3c', 'type': 'file_version', 'created_at': '2015-02-24T09:26:02-08:00'},
        ],
        'limit': 1000,
        'offset': 0,
        'total_count': 1,
    }


class TestDownload:

    @async
    @pytest.mark.aiohttpretty
    def test_download(self, provider, file_metadata):
        item = file_metadata['entries'][0]
        path = WaterButlerPath('/triangles.txt', _ids=(provider.folder, item['id']))

        metadata_url = provider.build_url('files', item['id'])
        content_url = provider.build_url('files', item['id'], 'content')

        aiohttpretty.register_json_uri('GET', metadata_url, body=item)
        aiohttpretty.register_uri('GET', content_url, body=b'better', auto_length=True)

        result = yield from provider.download(path)
        content = yield from result.read()

        assert content == b'better'

    @async
    @pytest.mark.aiohttpretty
    def test_download_not_found(self, provider, file_metadata):
        item = file_metadata['entries'][0]
        path = WaterButlerPath('/vectors.txt', _ids=(provider.folder, None))
        metadata_url = provider.build_url('files', item['id'])
        aiohttpretty.register_uri('GET', metadata_url, status=404)

        with pytest.raises(exceptions.DownloadError) as e:
            yield from provider.download(path)

        assert e.value.code == 404


class TestUpload:

    @async
    @pytest.mark.aiohttpretty
    def test_upload_create(self, provider, folder_object_metadata, folder_list_metadata, file_metadata, file_stream, settings):
        path = WaterButlerPath('/newfile', _ids=(provider.folder, None))

        upload_url = provider._build_upload_url('files', 'content')
        folder_object_url = provider.build_url('folders', path.parent.identifier)
        folder_list_url = provider.build_url('folders', path.parent.identifier, 'items')

        aiohttpretty.register_json_uri('POST', upload_url, status=201, body=file_metadata)

        metadata, created = yield from provider.upload(file_stream, path)

        path.parts[-1]._id = file_metadata['entries'][0]['id']
        expected = BoxFileMetadata(file_metadata['entries'][0], path).serialized()

        assert metadata == expected
        assert created is True
        assert aiohttpretty.has_call(method='POST', uri=upload_url)

    @async
    @pytest.mark.aiohttpretty
    def test_upload_update(self, provider, folder_object_metadata, folder_list_metadata, file_metadata, file_stream, settings):
        item = folder_list_metadata['entries'][0]
        path = WaterButlerPath('/newfile', _ids=(provider.folder, item['id']))
        upload_url = provider._build_upload_url('files', item['id'], 'content')
        aiohttpretty.register_json_uri('POST', upload_url, status=201, body=file_metadata)

        metadata, created = yield from provider.upload(file_stream, path)

        expected = BoxFileMetadata(file_metadata['entries'][0], path).serialized()

        assert metadata == expected
        assert created is False
        assert aiohttpretty.has_call(method='POST', uri=upload_url)


class TestDelete:

    @async
    @pytest.mark.aiohttpretty
    def test_delete_file(self, provider, file_metadata):
        item = file_metadata['entries'][0]
        path = WaterButlerPath('/{}'.format(item['name']), _ids=(provider.folder, item['id']))
        url = provider.build_url('files', path.identifier)

        aiohttpretty.register_uri('DELETE', url, status=204)

        yield from provider.delete(path)

        assert aiohttpretty.has_call(method='DELETE', uri=url)

    @async
    @pytest.mark.aiohttpretty
    def test_delete_folder(self, provider, folder_object_metadata):
        item = folder_object_metadata
        path = WaterButlerPath('/{}/'.format(item['name']), _ids=(provider.folder, item['id']))
        url = provider.build_url('folders', path.identifier, recursive=True)

        aiohttpretty.register_uri('DELETE', url, status=204)

        yield from provider.delete(path)

        assert aiohttpretty.has_call(method='DELETE', uri=url)

    @async
    def test_must_not_be_none(self, provider):
        path = WaterButlerPath('/Goats', _ids=(provider.folder, None))

        with pytest.raises(exceptions.NotFoundError) as e:
            yield from provider.delete(path)

        assert e.value.code == 404
        assert str(path) in e.value.message


class TestMetadata:

    @async
    def test_must_not_be_none(self, provider):
        path = WaterButlerPath('/Goats', _ids=(provider.folder, None))

        with pytest.raises(exceptions.NotFoundError) as e:
            yield from provider.metadata(path)

        assert e.value.code == 404
        assert str(path) in e.value.message

    @async
    @pytest.mark.aiohttpretty
    def test_metadata(self, provider, folder_object_metadata, folder_list_metadata):
        path = WaterButlerPath('/', _ids=(provider.folder, ))

        # object_url = provider.build_url('folders', provider.folder)
        list_url = provider.build_url('folders', provider.folder, 'items', fields='id,name,size,modified_at,etag')

        # aiohttpretty.register_json_uri('GET', object_url, body=folder_object_metadata)
        aiohttpretty.register_json_uri('GET', list_url, body=folder_list_metadata)

        result = yield from provider.metadata(path)

        expected = []

        for x in folder_list_metadata['entries']:
            if x['type'] == 'file':
                expected.append(BoxFileMetadata(x, path.child(x['name'])).serialized())
            else:
                expected.append(BoxFolderMetadata(x, path.child(x['name'])).serialized())

        assert result == expected

    # @async
    # @pytest.mark.aiohttpretty
    # def test_metadata_not_child(self, provider, folder_object_metadata):
    #     provider.folder += 'yourenotmydad'
    #     path = BoxPath('/' + provider.folder + '/')
    #     object_url = provider.build_url('folders', provider.folder)
    #     aiohttpretty.register_json_uri('GET', object_url, body=folder_object_metadata)

    #     with pytest.raises(exceptions.MetadataError) as exc_info:
    #         yield from provider.metadata(str(path))
    #     assert exc_info.value.code == 404

    # @async
    # @pytest.mark.aiohttpretty
    # def test_metadata_root_file(self, provider, file_metadata):
    #     path = BoxPath('/' + provider.folder + '/pfile')
    #     url = provider.build_url('files', path._id)
    #     aiohttpretty.register_json_uri('GET', url, body=file_metadata['entries'][0])
    #     result = yield from provider.metadata(str(path))

    #     assert isinstance(result, dict)
    #     assert result['kind'] == 'file'
    #     assert result['name'] == 'tigers.jpeg'
    #     assert result['path'] == '/5000948880/tigers.jpeg'

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_nested(self, provider, file_metadata):
        item = file_metadata['entries'][0]
        path = WaterButlerPath('/name.txt', _ids=(provider, item['id']))

        file_url = provider.build_url('files', path.identifier)
        aiohttpretty.register_json_uri('GET', file_url, body=item)

        result = yield from provider.metadata(path)

        expected = BoxFileMetadata(item, path).serialized()
        assert result == expected
        assert aiohttpretty.has_call(method='GET', uri=file_url)

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_missing(self, provider):
        path = WaterButlerPath('/Something', _ids=(provider.folder, None))

        with pytest.raises(exceptions.NotFoundError):
            yield from provider.metadata(path)


class TestRevisions:

    @async
    @pytest.mark.aiohttpretty
    def test_get_revisions(self, provider, file_metadata, revisions_list_metadata):
        item = file_metadata['entries'][0]

        path = WaterButlerPath('/name.txt', _ids=(provider, item['id']))

        file_url = provider.build_url('files', path.identifier)
        revisions_url = provider.build_url('files', path.identifier, 'versions')

        aiohttpretty.register_json_uri('GET', file_url, body=item)
        aiohttpretty.register_json_uri('GET', revisions_url, body=revisions_list_metadata)

        result = yield from provider.revisions(path)

        expected = [
            BoxRevision(each).serialized()
            for each in [item] + revisions_list_metadata['entries']
        ]

        assert result == expected
        assert aiohttpretty.has_call(method='GET', uri=file_url)
        assert aiohttpretty.has_call(method='GET', uri=revisions_url)

    @async
    @pytest.mark.aiohttpretty
    def test_get_revisions_free_account(self, provider, file_metadata):
        item = file_metadata['entries'][0]
        path = WaterButlerPath('/name.txt', _ids=(provider, item['id']))

        file_url = provider.build_url('files', path.identifier)
        revisions_url = provider.build_url('files', path.identifier, 'versions')

        aiohttpretty.register_json_uri('GET', file_url, body=item)
        aiohttpretty.register_json_uri('GET', revisions_url, body={}, status=403)

        result = yield from provider.revisions(path)
        expected = [BoxRevision(item).serialized()]
        assert result == expected
        assert aiohttpretty.has_call(method='GET', uri=file_url)
        assert aiohttpretty.has_call(method='GET', uri=revisions_url)


class TestCreateFolder:

    @async
    @pytest.mark.aiohttpretty
    def test_must_be_folder(self, provider):
        path = WaterButlerPath('/Just a poor file from a poor folder', _ids=(provider.folder, None))

        with pytest.raises(exceptions.CreateFolderError) as e:
            yield from provider.create_folder(path)

        assert e.value.code == 400
        assert e.value.message == 'Path must be a directory'

    @async
    @pytest.mark.aiohttpretty
    def test_id_must_be_none(self, provider):
        path = WaterButlerPath('/Just a poor file from a poor folder/', _ids=(provider.folder, 'someid'))

        assert path.identifier is not None

        with pytest.raises(exceptions.FolderNamingConflict) as e:
            yield from provider.create_folder(path)

        assert e.value.code == 409
        assert e.value.message == 'Cannot create folder "Just a poor file from a poor folder" because a file or folder already exists at path "/Just a poor file from a poor folder/"'

    @async
    @pytest.mark.aiohttpretty
    def test_already_exists(self, provider):
        url = provider.build_url('folders')
        data_url = provider.build_url('folders', provider.folder)
        path = WaterButlerPath('/50 shades of nope/', _ids=(provider.folder, None))

        aiohttpretty.register_json_uri('POST', url, status=409)
        aiohttpretty.register_json_uri('GET', data_url, body={
            'id': provider.folder,
            'type': 'folder',
            'name': 'All Files',
            'path_collection': {
                'entries': []
            }
        })

        with pytest.raises(exceptions.FolderNamingConflict) as e:
            yield from provider.create_folder(path)

        assert e.value.code == 409
        assert e.value.message == 'Cannot create folder "50 shades of nope" because a file or folder already exists at path "/50 shades of nope/"'

    @async
    @pytest.mark.aiohttpretty
    def test_returns_metadata(self, provider, folder_object_metadata):
        url = provider.build_url('folders')
        folder_object_metadata['name'] = '50 shades of nope'
        path = WaterButlerPath('/50 shades of nope/', _ids=(provider.folder, None))

        aiohttpretty.register_json_uri('POST', url, status=201, body=folder_object_metadata)

        resp = yield from provider.create_folder(path)

        assert resp['kind'] == 'folder'
        assert resp['name'] == '50 shades of nope'
        assert resp['path'] == '/{}/'.format(folder_object_metadata['id'])
