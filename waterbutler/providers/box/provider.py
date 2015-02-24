import http
import json
import asyncio

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.box import settings
from waterbutler.providers.box.metadata import BoxRevision
from waterbutler.providers.box.metadata import BoxFileMetadata
from waterbutler.providers.box.metadata import BoxFolderMetadata


class BoxPath(utils.WaterButlerPath):

    def __init__(self, path, prefix=False, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)
        if path != '/':
            self._id = path.split('/')[1]
        else:
            self._id = path


class BoxProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.folder = self.settings['folder']

    @property
    def default_headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token),
        }

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        meta = yield from self.metadata(path, raw=True)
        query = {}
        if revision and revision != meta['id']:
            query['version'] = revision
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', meta['id'], 'content', **query),
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        parts = path.split('/')
        if len(parts) == 2:
            parts.insert(1, self.folder)
        _, parent_id, name = parts
        parent_path = '/{}/'.format(parent_id)
        meta = yield from self.metadata(parent_path, raw=True)
        matches = [each for each in meta['entries'] if each['name'] == name]
        if matches:
            created = False
            data = yield from self._send_upload(stream, name, parent_id, matches[0]['id'])
        else:
            created = True
            data = yield from self._send_upload(stream, name, parent_id)

        return BoxFileMetadata(data['entries'][0], self.folder).serialized(), created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        metadata = yield from self.metadata(path, raw=True)
        yield from self.make_request(
            'DELETE',
            self.build_url('files', metadata['id']),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, raw=False, **kwargs):
        path = BoxPath(path)

        if path.is_file:
            return (yield from self._get_file_meta(path, raw=raw))
        return (yield from self._get_folder_meta(path, raw=raw))

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        #from https://developers.box.com/docs/#files-view-versions-of-a-file :
        #Alert: Versions are only tracked for Box users with premium accounts.
        #Few users will have a premium account, return only current if not
        path = BoxPath(path)
        response = yield from self.make_request(
            'GET',
            self.build_url('files', path._id, 'versions'),
            expects=(200, ),
            throws=exceptions.RevisionsError,
        )
        data = yield from response.json()

        ret = []
        curr = yield from self.metadata(str(path))
        ret.append(BoxRevision(curr).serialized())

        for item in data['entries']:
            ret.append(BoxRevision(item).serialized())

        return ret

    def _assert_child(self, paths, target=None):
        if target == self.folder:
            return True
        if not paths:
            raise exceptions.MetadataError('Not found', code=http.client.NOT_FOUND)
        if paths[0]['id'] == self.folder:
            return True
        return self._assert_child(paths[1:])

    @asyncio.coroutine
    def _assert_child_folder(self, path):
        response = yield from self.make_request(
            'GET',
            self.build_url('folders', path._id),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        data = yield from response.json()
        self._assert_child(data['path_collection']['entries'], target=data['id'])

    @asyncio.coroutine
    def _get_file_meta(self, path, raw=False):
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', path._id),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        data = yield from resp.json()

        if not data:
            raise exceptions.NotFoundError(str(path))

        self._assert_child(data['path_collection']['entries'])

        return data if raw else BoxFileMetadata(data, self.folder).serialized()

    @asyncio.coroutine
    def _get_folder_meta(self, path, raw=False):
        if str(path) == '/':
            path = BoxPath('/{}/'.format(self.folder))

        yield from self._assert_child_folder(path)

        response = yield from self.make_request(
            'GET',
            self.build_url('folders', path._id, 'items'),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        data = yield from response.json()

        if raw:
            return data

        return [
            self._serialize_item(each)
            for each in data['entries']
        ]

    def _serialize_item(self, item):
        if item['type'] == 'folder':
            serializer = BoxFolderMetadata
        else:
            serializer = BoxFileMetadata
        return serializer(item, self.folder).serialized()

    def _send_upload(self, stream, name, parent_id, file_id=None):
        data_stream = streams.FormDataStream(
            attributes=json.dumps({'name': name, 'parent': {'id': parent_id}}),
        )
        segments = ['files', 'content']
        if file_id:
            segments.insert(1, file_id)
        data_stream.add_file('file', stream, name, disposition='form-data')
        resp = yield from self.make_request(
            'POST',
            self._build_upload_url(*segments),
            data=data_stream,
            headers=data_stream.headers,
            expects=(201, ),
            throws=exceptions.UploadError,
        )
        return (yield from resp.json())

    def _build_upload_url(self, *segments, **query):
        return provider.build_url(settings.BASE_UPLOAD_URL, *segments, **query)
