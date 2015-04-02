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


class GoogleDrivePath(utils.WaterButlerPath):

    def __init__(self, folder, path, prefix=True, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)
        self._folder = folder
        full_path = os.path.join(folder, path.lstrip('/'))
        self._full_path = self._format_path(full_path)

    @property
    def parent(self):
        cls = self.__class__
        return cls(self._folder, '/'.join(self._parts[:-1]) + '/', prefix=self._prefix, suffix=self._suffix)

    @property
    def child(self):
        cls = self.__class__
        path = '/' + '/'.join(self._parts[2:])
        if self.is_dir:
            path += '/'
        path = path.replace('//', '/')
        return cls(self._folder, path, prefix=self._prefix, suffix=self._suffix)

    @property
    def path(self):
        return parse.unquote(self._path)

    @property
    def parts(self):
        return [parse.unquote(x) for x in self._parts]

    @property
    def name(self):
        return parse.unquote(self._parts[-1])


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
        name = '/' + parse.quote(path.pop(-1))

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
            segments = (exists['id'])
        else:
            segments = ()

        upload_metadata = self._build_upload_metadata(parent_id, path.name)
        upload_id = yield from self._start_resumable_upload(not exists, segments, stream.size, upload_metadata)
        data = yield from self._finish_resumable_upload(segments, stream, upload_id)

        return GoogleDriveFileMetadata(data, path.parent).serialized(), not exists

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        path = GoogleDrivePath(self.folder['name'], path)
        metadata = yield from self.metadata(str(path), raw=True)
        yield from self.make_request(
            'DELETE',
            self.build_url('files', metadata['id']),
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
