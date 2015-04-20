import os
import http
import json
import asyncio
from urllib import parse

import furl

from waterbutler.core import utils
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

    @property
    def default_headers(self):
        return {'authorization': 'Bearer {}'.format(self.token)}

    @asyncio.coroutine
    def copy(self, dest_provider, source_options, dest_options):
        path, name = os.path.split(dest_options['path'])
        dest_options['path'] = os.path.join(path, parse.unquote(name))
        return (yield from super().copy(dest_provider, source_options, dest_options))

    def can_intra_move(self, other):
        return self == other

    def can_intra_copy(self, other):
        return self == other

    @asyncio.coroutine
    def intra_move(self, destination_provider, source_options, destination_options):
        source_path = GoogleDrivePath(self.folder['name'], source_options['path'])
        destination_path = GoogleDrivePath(destination_provider.folder['name'], destination_options['path'])

        source_id = yield from self._materialized_path_to_id(source_path)
        destination_id = yield from destination_provider._materialized_path_to_id(destination_path.parent)

        path, exists = yield from self.handle_name_conflict(
            GoogleDrivePath(destination_provider.folder['name'], '/' + parse.quote(destination_path.name, safe='')),
            raw=True,
            parent_id=destination_id,
            conflict=destination_options.get('conflict'),
        )

        if destination_options.get('conflict') != 'keep' and exists:
            yield from destination_provider.delete(None, item_id=exists['id'])

        resp = yield from self.make_request(
            'PATCH',
            self.build_url('files', source_id),
            headers={
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'parents': [{
                    'id': destination_id
                }],
                'title': path.name
            }),
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )

        data = yield from resp.json()
        return GoogleDriveFileMetadata(data, destination_path.parent).serialized(), not exists

    @asyncio.coroutine
    def intra_copy(self, destination, source_options, destination_options):
        source_path = GoogleDrivePath(self.folder['name'], source_options['path'])
        destination_path = GoogleDrivePath(destination_provider.folder['name'], destination_options['path'])

        source_id = yield from self._materialized_path_to_id(source_path)
        destination_id = yield from destination_provider._materialized_path_to_id(destination_path.parent)

        path, exists = yield from self.handle_name_conflict(
            GoogleDrivePath(destination_provider.folder['name'], '/' + parse.quote(destination_path.name, safe='')),
            raw=True,
            parent_id=destination_id,
            conflict=destination_options.get('conflict'),
        )

        if destination_options.get('conflict') != 'keep' and exists:
            yield from destination_provider.delete(None, item_id=exists['id'])

        resp = yield from self.make_request(
            'POST',
            self.build_url('files', source_id, 'copy'),
            headers={
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'parents': [{
                    'id': destination_id
                }],
                'title': path.name
            }),
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )

        data = yield from resp.json()
        return GoogleDriveFileMetadata(data, destination_path).serialized(), not exists

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        data = yield from self.metadata(path, raw=True)
        if revision and not revision.endswith(settings.DRIVE_IGNORE_VERSION):
            # Must make additional request to look up download URL for revision
            response = yield from self.make_request(
                'GET',
                self.build_url('files', data['id'], 'revisions', revision, alt='json'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            data = yield from response.json()

        try:
            download_url = data['downloadUrl']
        except KeyError:
            download_url = drive_utils.get_export_link(data['exportLinks'])

        download_resp = yield from self.make_request(
            'GET',
            download_url,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        return streams.ResponseStreamReader(download_resp)

    @asyncio.coroutine
    def upload(self, stream, path, conflict='replace', **kwargs):
        path = path.split('/')
        name = '/' + parse.quote(path.pop(-1), safe='')

        parent_id = yield from self._materialized_path_to_id(
            GoogleDrivePath(
                self.folder['name'],
                ('/'.join(path) or '/')
            )
        )

        path, exists = yield from self.handle_name_conflict(
            GoogleDrivePath(self.folder['name'], name),
            raw=True,
            conflict=conflict,
            parent_id=parent_id,
        )

        if exists:
            segments = (exists['id'], )
        else:
            segments = ()

        upload_metadata = self._build_upload_metadata(parent_id, path.name)
        upload_id = yield from self._start_resumable_upload(not exists, segments, stream.size, upload_metadata)
        data = yield from self._finish_resumable_upload(segments, stream, upload_id)

        return GoogleDriveFileMetadata(data, path.parent).serialized(), not exists

    @asyncio.coroutine
    def delete(self, path, item_id=None, **kwargs):
        if not item_id:
            path = GoogleDrivePath(self.folder['name'], path)
            metadata = yield from self.metadata(str(path), raw=True)
            item_id = metadata['id']

        yield from self.make_request(
            'DELETE',
            self.build_url('files', item_id),
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
    def metadata(self, path, raw=False, parent_id=None, **kwargs):
        path = GoogleDrivePath(self.folder['name'], path)
        item_id = yield from self._materialized_path_to_id(path, parent_id=parent_id)

        if path.is_dir:
            return (yield from self._folder_metadata(path, item_id, raw=raw))

        return (yield from self._file_metadata(path, item_id, raw=raw))

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        metadata = yield from self.metadata(path, raw=True)
        response = yield from self.make_request(
            'GET',
            self.build_url('files', metadata['id'], 'revisions'),
            expects=(200, ),
            throws=exceptions.RevisionsError,
        )
        data = yield from response.json()
        if data['items']:
            return [
                GoogleDriveRevision(item).serialized()
                for item in reversed(data['items'])
            ]

        # Use dummy ID if no revisions found
        return [GoogleDriveRevision({
            'modifiedDate': metadata['modifiedDate'],
            'id': data['etag'] + settings.DRIVE_IGNORE_VERSION,
        }).serialized()]

    @asyncio.coroutine
    def create_folder(self, path, **kwargs):
        path = GoogleDrivePath(self.folder['name'], path)
        path.validate_folder()

        try:
            yield from self.metadata(str(path), raw=True)
            raise exceptions.CreateFolderError('Folder "{}" already exists.'.format(str(path)), code=409)
        except exceptions.MetadataError as e:
            if e.code != 404:
                raise

        if path.parent.is_root:
            folder_id = self.folder['id']
        else:
            parent_path = str(path.parent).rstrip('/')
            metadata = yield from self.metadata(parent_path, raw=True)
            folder_id = metadata['id']

        resp = yield from self.make_request(
            'POST',
            self.build_url('files'),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': path.name,
                'parents': [{
                    'id': folder_id
                }],
                'mimeType': 'application/vnd.google-apps.folder'
            }),
            expects=(200, ),
            throws=exceptions.CreateFolderError,
        )

        return GoogleDriveFolderMetadata((yield from resp.json()), path.parent).serialized()

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
    def _resolve_path_to_ids(self, path):
        if path == '/':
            return [{
                'id': self.folder['id'],
                'title': self.folder['name']
            }]

        parts = []
        item_id = self.folder['id']
        parts = path.strip('/').split('/')

        while parts:
            current_part = parts.pop(0)

            resp = yield from self.make_request(
                'GET',
                self.build_url('files', item_id, 'children', q='title = "{}"', fields='id'.format(current_part)),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )

            try:
                item_id = (yield from resp.json())['items'][0]['id']
            except (KeyError, IndexError):
                raise exceptions.MetadataError('{} not found'.format(str(path)), code=http.client.NOT_FOUND)

            parts.append({
                'id': item['id'],
                'title': current_part
            })

        return parts

    @asyncio.coroutine
    def _resolve_id_to_parts(self, _id, accum=None):
        if _id == self.folder['id']:
            return [self.folder] + (accum or [])

        if accum is None:
            resp = yield from self.make_request(
                'GET',
                self.build_url('files', _id, fields='id,title'),
                expects=(200, ),
                throws=exceptions.MetadataError,
            )
            accum = [(yield from resp.json())]

        for parent in (yield from self._get_parent_ids(_id)):
            if self.folder['id'] == parent['id']:
                return [parent] + (accum or [])
                try:
                    return (yield from _resolve_id_to_parts(
                        self, parent['id'],
                        [parent] + (accum or [])
                    ))
                except exceptions.MetadataError:
                    pass

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
            self.build_url('files', data['id'], 'revisions'),
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
    def _folder_metadata(self, path, item_id, raw=False):
        query = self._build_query(item_id)
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
    def _file_metadata(self, path, item_id, raw=False):
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', item_id),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        data = yield from resp.json()

        if drive_utils.is_docs_file(data):
            return (yield from self._handle_docs_versioning(data))

        return self._serialize_item(path, data, raw=raw)
