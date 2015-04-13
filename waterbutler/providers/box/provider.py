import os
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

    def __init__(self, path, _id=None, prefix=False, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)
        try:
            self._id = str(int(self.parts[1]))
        except:
            self._id = _id

class BoxProvider(provider.BaseProvider):
    NAME = 'box'
    BASE_URL = settings.BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.folder = self.settings['folder']

    def can_intra_move(self, other):
        return self == other

    def can_intra_copy(self, other):
        return self == other

    def intra_copy(self, destination_provider, source_options, destination_options):
        source_path = BoxPath(source_options['path'], _id=self.folder)
        destination_path = BoxPath(destination_options['path'], _id=destination_provider.folder)

        #TODO Refactor this into handle_name_conflict
        conflicting_id = yield from destination_provider._check_conflict(destination_path)

        if conflicting_id:
            if destination_options.get('conflict') != 'keep':
                yield from destination_provider.delete(file_id=conflicting_id, **destination_options)
            else:
                while conflicting_id:
                    destination_path.increment_name()
                    conflicting_id = yield from destination_provider._check_conflict(destination_path)

        resp = yield from self.make_request(
            'POST',
            self.build_url('files', source_path._id, 'copy'),
            data=json.dumps({
                'name': destination_path.name,
                'parent': {
                    'id': destination_path._id
                }
            }),
            headers={'Content-Type': 'application/json'},
            expects=(200, 201),
            throws=exceptions.IntraCopyError
        )

        data = yield from resp.json()

        data['fullPath'] = self._build_full_path(data['path_collection']['entries'][1:], destination_path.name)
        return BoxFileMetadata(data, destination_provider.folder).serialized(), conflicting_id is None

    @property
    def default_headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token),
        }

    @asyncio.coroutine
    def make_request(self, *args, **kwargs):
        if isinstance(kwargs.get('data'), dict):
            kwargs['data'] = json.dumps(kwargs['data'])

        return super().make_request(*args, **kwargs)

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
    def upload(self, stream, path, file_id=None, conflict='replace', box_path=None, **kwargs):
        path = box_path or BoxPath(path, _id=self.folder)

        preflight_resp = yield from self.make_request(
            'OPTIONS',
            self.build_url(*filter(lambda x: x is not None, ('files', file_id, 'content'))),
            data=json.dumps({
                'name': path.name,
                'parent': {
                    'id': path._id
                }
            }),
            headers={'Content-Type': 'application/json'},
            expects=(200, 409),
            throws=exceptions.UploadError,
        )

        preflight = yield from preflight_resp.json()

        if preflight_resp.status == 409:
            if preflight['context_info']['conflicts']['type'] != 'file':
                raise exceptions.UploadError(code=409)

            if conflict == 'keep':
                return (yield from self.upload(
                    stream,
                    str(path),
                    conflict=conflict,
                    box_path=path.increment_name(),
                    **kwargs
                ))
            else:
                return (yield from self.upload(
                    stream,
                    str(path),
                    conflict=conflict,
                    box_path=path,
                    file_id=preflight['context_info']['conflicts']['id'],
                    **kwargs
                ))

        data_stream = streams.FormDataStream(
            attributes=json.dumps({'name': path.name, 'parent': {'id': path._id}}),
        )
        data_stream.add_file('file', stream, path.name, disposition='form-data')

        resp = yield from self.make_request(
            'POST',
            self._build_upload_url(*filter(lambda x: x is not None, ('files', file_id, 'content'))),
            data=data_stream,
            headers=data_stream.headers,
            expects=(201, 409),
            throws=exceptions.UploadError,
        )

        data = yield from resp.json()

        data['entries'][0]['fullPath'] = self._build_full_path(data['entries'][0]['path_collection']['entries'][1:], path.name)
        return BoxFileMetadata(data['entries'][0], self.folder).serialized(), file_id is None

    @asyncio.coroutine
    def delete(self, path, file_id=None, folder_id=None, **kwargs):
        if not file_id or not folder_id:
            path = BoxPath(path)
            metadata = yield from self.metadata(str(path), raw=True, folder=path.is_dir)
            if path.is_file:
                file_id = metadata['id']
            else:
                folder_id = metadata['id']

        if file_id:
            url = self.build_url('files', file_id)
        else:
            url = self.build_url('folders', folder_id, recursive=True)

        yield from self.make_request(
            'DELETE',
            url,
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, raw=False, folder=False, **kwargs):
        path = BoxPath(path)
        if path.is_file:
            return (yield from self._get_file_meta(path, raw=raw))
        return (yield from self._get_folder_meta(path, raw=raw, folder=folder))

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        #from https://developers.box.com/docs/#files-view-versions-of-a-file :
        #Alert: Versions are only tracked for Box users with premium accounts.
        #Few users will have a premium account, return only current if not
        path = BoxPath(path)
        curr = yield from self.metadata(str(path), raw=True)
        response = yield from self.make_request(
            'GET',
            self.build_url('files', path._id, 'versions'),
            expects=(200, 403),
            throws=exceptions.RevisionsError,
        )
        data = yield from response.json()

        revisions = data['entries'] if response.status == http.client.OK else []

        return [
            BoxRevision(each).serialized()
            for each in [curr] + revisions
        ]

    @asyncio.coroutine
    def create_folder(self, path, **kwargs):
        if len(path.split('/')) == 3:
            path = '/{}{}'.format(self.folder, path)

        path = BoxPath(path)
        path.validate_folder()

        resp = yield from self.make_request(
            'POST',
            self.build_url('folders'),
            data={
                'name': path.name,
                'parent': {
                    'id': path._id or self.folder
                }
            },
            expects=(201, 409),
            throws=exceptions.CreateFolderError,
        )

        if resp.status == 409:
            raise exceptions.CreateFolderError('Folder "{}" already exists.'.format(str(path)), code=409)

        return BoxFolderMetadata(
            (yield from resp.json()),
            self.folder
        ).serialized()

    def _assert_child(self, paths, target=None):
        if self.folder == 0:
            return True
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
    def _get_folder_meta(self, path, raw=False, folder=False):
        if str(path) == '/':
            path = BoxPath('/{}/'.format(self.folder))
        yield from self._assert_child_folder(path)

        if folder:
            url = self.build_url('folders', path._id)
        else:
            url = self.build_url('folders', path._id, 'items')

        response = yield from self.make_request(
            'GET',
            url,
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

    def _build_upload_url(self, *segments, **query):
        return provider.build_url(settings.BASE_UPLOAD_URL, *segments, **query)

    def _build_full_path(self, entries, filename):
        path = []
        for entry in reversed(entries):
            if self.folder == entry['id']:
                break
            path.append(entry['name'])

        path = '/'.join(reversed(path))
        return '/' + os.path.join(path, filename)

    @asyncio.coroutine
    def _check_conflict(self, path, kind='files'):
        """Check if there would be a conflict upon upload/copy/moving/etc
        a file to the given path

        :param str url: The url to check against
        :param BoxPath path: The path in question

        :rtype: None or str
        :returns: The id of the existing file or None
        """

        resp = yield from self.make_request(
            'OPTIONS',
            self.build_url(kind, 'content'),
            data=json.dumps({
                'name': path.name,
                'parent': {
                    'id': path._id
                }
            }),
            headers={'Content-Type': 'application/json'},
            expects=(200, 409),
            throws=exceptions.ProviderError
        )

        if resp.status == 200:
            return None

        data = yield from resp.json()

        if data['context_info']['conflicts']['type'] != 'file':
            raise exceptions.ProviderError(code=409)

        return data['context_info']['conflicts']['id']
