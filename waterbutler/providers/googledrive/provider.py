import http
import json
import asyncio
import functools
from urllib import parse

import furl

from waterbutler.core import path
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.googledrive import settings
from waterbutler.providers.googledrive import utils as drive_utils
from waterbutler.providers.googledrive.metadata import GoogleDriveRevision
from waterbutler.providers.googledrive.metadata import GoogleDriveFileMetadata
from waterbutler.providers.googledrive.metadata import GoogleDriveFolderMetadata

class GoogleDrivePathPart(path.WaterButlerPathPart):
    DECODE = parse.unquote
    ENCODE = functools.partial(parse.quote, safe='')

class GoogleDrivePath(path.WaterButlerPath):
    PART_CLASS = GoogleDrivePathPart


class GoogleDriveProvider(provider.BaseProvider):
    NAME = 'googledrive'
    BASE_URL = settings.BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.folder = self.settings['folder']

    @asyncio.coroutine
    def validate_path(self, path, file_id=None, **kwargs):
        if path == '/':
            return GoogleDrivePath('/', _ids=[self.folder['id']], folder=True)

        parts = yield from self._resolve_path_to_ids(path)

        # TODO Allow for just passing file_id
        # if file_id:
        #     parts = yield from self._resolve_id_to_parts(file_id)
        # elif path:
        # else:
        #     raise Exception  # TODO

        names, ids = zip(*[(parse.quote(x['title'], safe=''), x['id']) for x in parts])
        return GoogleDrivePath('/'.join(names), _ids=ids, folder='folder' in parts[-1]['mimeType'])

    @asyncio.coroutine
    def revalidate_path(self, base, name, folder=None):
        parts = yield from self._resolve_path_to_ids(name, start_at=[{
            'title': base.name,
            'mimeType': 'folder',
            'id': base.identifier,
        }])
        _id, name, mime = list(map(parts[-1].__getitem__, ('id', 'title', 'mimeType')))
        return base.child(name, _id=_id, folder='folder' in mime)

    @property
    def default_headers(self):
        return {'authorization': 'Bearer {}'.format(self.token)}

    def can_intra_move(self, other, path=None):
        return self == other

    def can_intra_copy(self, other, path=None):
        return self == other and (path and path.is_file)

    @asyncio.coroutine
    def intra_move(self, dest_provider, src_path, dest_path):
        if dest_path.identifier:
            yield from dest_provider.delete(dest_path)

        resp = yield from self.make_request(
            'PATCH',
            self.build_url('files', src_path.identifier),
            headers={
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'parents': [{
                    'id': dest_path.parent.identifier
                }],
                'title': dest_path.name
            }),
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )

        data = yield from resp.json()
        return GoogleDriveFileMetadata(data, dest_path.parent).serialized(), dest_path.identifier is None

    @asyncio.coroutine
    def intra_copy(self, dest_provider, src_path, dest_path):
        if dest_path.identifier:
            yield from dest_provider.delete(dest_path)

        resp = yield from self.make_request(
            'POST',
            self.build_url('files', src_path.identifier, 'copy'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'parents': [{
                    'id': dest_path.parent.identifier
                }],
                'title': dest_path.name
            }),
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )

        data = yield from resp.json()
        return GoogleDriveFileMetadata(data, dest_path.parent).serialized(), dest_path.identifier is None

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        if revision and not revision.endswith(settings.DRIVE_IGNORE_VERSION):
            # Must make additional request to look up download URL for revision
            response = yield from self.make_request(
                'GET',
                self.build_url('files', path.identifier, 'revisions', revision, alt='json'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            data = yield from response.json()
        else:
            data = yield from self.metadata(path, raw=True)

        download_resp = yield from self.make_request(
            'GET',
            data.get('downloadUrl') or drive_utils.get_export_link(data['exportLinks']),
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        return streams.ResponseStreamReader(download_resp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        assert path.is_file

        if path.identifier:
            segments = (path.identifier, )
        else:
            segments = ()

        upload_metadata = self._build_upload_metadata(path.parent.identifier, path.name)
        upload_id = yield from self._start_resumable_upload(not path.identifier, segments, stream.size, upload_metadata)
        data = yield from self._finish_resumable_upload(segments, stream, upload_id)

        return GoogleDriveFileMetadata(data, path).serialized(), path.identifier is None

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        if not path.identifier:
            raise exceptions.NotFoundError(str(path))

        yield from self.make_request(
            'DELETE',
            self.build_url('files', path.identifier),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    def _build_query(self, folder_id, title=None):
        queries = [
            "'{}' in parents".format(folder_id),
            'trashed = false',
        ]
        if title:
            queries.append("title = '{}'".format(title.replace("'", "\\'")))
        return ' and '.join(queries)

    @asyncio.coroutine
    def metadata(self, path, raw=False, **kwargs):
        if path.identifier is None:
            raise exceptions.MetadataError('{} not found'.format(str(path)), code=404)

        if path.is_dir:
            return (yield from self._folder_metadata(path, raw=raw))

        return (yield from self._file_metadata(path, raw=raw))

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        if path.identifier is None:
            raise exceptions.NotFoundError(str(path))

        response = yield from self.make_request(
            'GET',
            self.build_url('files', path.identifier, 'revisions'),
            expects=(200, ),
            throws=exceptions.RevisionsError,
        )
        data = yield from response.json()
        if data['items']:
            return [
                GoogleDriveRevision(item).serialized()
                for item in reversed(data['items'])
            ]

        metadata = yield from self.metadata(path, raw=True)

        # Use dummy ID if no revisions found
        return [GoogleDriveRevision({
            'modifiedDate': metadata['modifiedDate'],
            'id': data['etag'] + settings.DRIVE_IGNORE_VERSION,
        }).serialized()]

    @asyncio.coroutine
    def create_folder(self, path, **kwargs):
        GoogleDrivePath.validate_folder(path)

        if path.identifier:
            raise exceptions.FolderNamingConflict(str(path))

        resp = yield from self.make_request(
            'POST',
            self.build_url('files'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': path.name,
                'parents': [{
                    'id': path.parent.identifier
                }],
                'mimeType': 'application/vnd.google-apps.folder'
            }),
            expects=(200, ),
            throws=exceptions.CreateFolderError,
        )

        return GoogleDriveFolderMetadata((yield from resp.json()), path).serialized()

    def _build_upload_url(self, *segments, **query):
        return provider.build_url(settings.BASE_UPLOAD_URL, *segments, **query)

    def _serialize_item(self, path, item, raw=False):
        if raw:
            return item
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            return GoogleDriveFolderMetadata(item, path).serialized()
        return GoogleDriveFileMetadata(item, path).serialized()

    def _build_upload_metadata(self, folder_id, name):
        return {
            'parents': [
                {
                    'kind': 'drive#parentReference',
                    'id': folder_id,
                },
            ],
            'title': name,
        }

    @asyncio.coroutine
    def _start_resumable_upload(self, created, segments, size, metadata):
        resp = yield from self.make_request(
            'POST' if created else 'PUT',
            self._build_upload_url('files', *segments, uploadType='resumable'),
            headers={
                'Content-Type': 'application/json',
                'X-Upload-Content-Length': str(size),
            },
            data=json.dumps(metadata),
            expects=(200, ),
            throws=exceptions.UploadError,
        )
        location = furl.furl(resp.headers['LOCATION'])
        return location.args['upload_id']

    @asyncio.coroutine
    def _finish_resumable_upload(self, segments, stream, upload_id):
        resp = yield from self.make_request(
            'PUT',
            self._build_upload_url('files', *segments, uploadType='resumable', upload_id=upload_id),
            headers={'Content-Length': str(stream.size)},
            data=stream,
            expects=(200, ),
            throws=exceptions.UploadError,
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _materialized_path_to_id(self, path, parent_id=None):
        parts = path.parts
        item_id = parent_id or self.folder['id']

        while parts:
            resp = yield from self.make_request(
                'GET',
                self.build_url('files', item_id, 'children', q='title = "{}"'.format(parts.pop(0))),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            try:
                item_id = (yield from resp.json())['items'][0]['id']
            except (KeyError, IndexError):
                raise exceptions.MetadataError('{} not found'.format(str(path)), code=http.client.NOT_FOUND)

        return item_id

    @asyncio.coroutine
    def _resolve_path_to_ids(self, path, start_at=None):
        ret = start_at or [{
            'title': '',
            'mimeType': 'folder',
            'id': self.folder['id'],
        }]
        item_id = ret[0]['id']
        parts = [parse.unquote(x) for x in path.strip('/').split('/')]

        while parts:
            current_part = parts.pop(0)

            resp = yield from self.make_request(
                'GET',
                self.build_url('files', item_id, 'children', q='title = "{}"'.format(current_part.replace('"', '\\"')), fields='items(id)'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )

            try:
                item_id = (yield from resp.json())['items'][0]['id']
            except (KeyError, IndexError):
                if parts:
                    raise exceptions.MetadataError('{} not found'.format(str(path)), code=http.client.NOT_FOUND)
                return ret + [{
                    'id': None,
                    'title': current_part,
                    'mimeType': 'folder' if path.endswith('/') else '',
                }]

            resp = yield from self.make_request(
                'GET',
                self.build_url('files', item_id, fields='id,title,mimeType'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )

            ret.append((yield from resp.json()))

        return ret

    @asyncio.coroutine
    def _resolve_id_to_parts(self, _id, accum=None):
        if _id == self.folder['id']:
            return [{
                'title': '',
                'mimeType': 'folder',
                'id': self.folder['id'],
            }] + (accum or [])

        if accum is None:
            resp = yield from self.make_request(
                'GET',
                self.build_url('files', _id, fields='id,title,mimeType'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            accum = [(yield from resp.json())]

        for parent in (yield from self._get_parent_ids(_id)):
            if self.folder['id'] == parent['id']:
                return [parent] + (accum or [])
                try:
                    return (yield from self._resolve_id_to_parts(
                        self, parent['id'],
                        [parent] + (accum or [])
                    ))
                except exceptions.MetadataError:
                    pass

        # TODO Custom exception here
        raise exceptions.MetadataError('ID is out of scope')

    @asyncio.coroutine
    def _get_parent_ids(self, _id):
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', _id, 'parents', fields='items(id)'),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        parents = []
        for parent in (yield from resp.json())['items']:
            p_resp = yield from self.make_request(
                'GET',
                self.build_url('files', parent['id'], fields='id,title'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            parents.append((yield from p_resp.json()))
        return parents

    @asyncio.coroutine
    def _handle_docs_versioning(self, path, item, raw=True):
        revisions_response = yield from self.make_request(
            'GET',
            self.build_url('files', item['id'], 'revisions'),
            expects=(200, ),
            throws=exceptions.RevisionsError,
        )
        revisions_data = yield from revisions_response.json()

        # Revisions are not available for some sharing configurations. If
        # revisions list is empty, use the etag of the file plus a sentinel
        # string as a dummy revision ID.
        if not revisions_data['items']:
            # If there are no revisions use etag as vid
            item['version'] = revisions_data['etag'] + settings.DRIVE_IGNORE_VERSION
        else:
            item['version'] = revisions_data['items'][-1]['id']

        return self._serialize_item(path, item, raw=raw)

    @asyncio.coroutine
    def _folder_metadata(self, path, raw=False):
        query = self._build_query(path.identifier)

        resp = yield from self.make_request(
            'GET',
            self.build_url('files', q=query, alt='json'),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        data = yield from resp.json()

        return [
            self._serialize_item(path, item, raw=raw)
            for item in data['items']
        ]

    @asyncio.coroutine
    def _file_metadata(self, path, raw=False):
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', path.identifier),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        data = yield from resp.json()

        if drive_utils.is_docs_file(data):
            return (yield from self._handle_docs_versioning(path, data, raw=raw))

        return self._serialize_item(path, data, raw=raw)
