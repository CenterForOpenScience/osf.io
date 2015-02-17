import os
import asyncio
import json

import requests

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.box import settings
from waterbutler.providers.box.metadata import BoxRevision
from waterbutler.providers.box.metadata import BoxFileMetadata
from waterbutler.providers.box.metadata import BoxFolderMetadata


class BoxPath(utils.WaterButlerPath):

    def __init__(self, path):
        super().__init__(path, prefix=False, suffix=False)
        if path != '/':
            self._id = path.split('/')[1]
        else:
            self._id = path


class BoxProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL
    BASE_UPLOAD_URL = settings.BASE_UPLOAD_URL

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
        path = BoxPath(path)
        if revision and revision != path._id:
            url = self.build_url('files', path._id, 'content', version=revision)
        else:
            url = self.build_url('files', path._id, 'content')

        resp = yield from self.make_request(
            'GET',
            url,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        path = BoxPath('/{}{}'.format(self.folder.lstrip('/'), path))
        try:
            meta = yield from self.metadata(str(path))
        except exceptions.MetadataError:
            created = True
            data = yield from self._upload_create(stream, path)
        else:
            created = False
            data = yield from self._upload_update(stream, path, meta)

        return BoxFileMetadata(data['entries'][0], self.folder).serialized(), created

    @asyncio.coroutine 
    def delete(self, path, **kwargs):
        #'etag' of the file can be included as an ‘If-Match’ header to prevent race conditions
        path = BoxPath(path)

        yield from self.make_request(
            'DELETE',
            self.build_url('files', path._id),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        path = BoxPath(path)

        if path.is_file:
            return self._get_file_meta(path)
        else:
            return self._get_folder_meta(path)


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
            throws=exceptions.RevisionsError
        )
        data = yield from response.json()

        ret = []
        curr = yield from self.metadata(str(path))
        ret.append(BoxRevision(curr).serialized())

        for item in data['entries']:
            ret.append(BoxRevision(item).serialized())

        return ret

    def _get_file_meta(self, path):
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', path._id),
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()
        if data:
            return BoxFileMetadata(data, self.folder).serialized()
        
        raise exceptions.MetadataError('Unable to find file.')

    def _get_folder_meta(self, path):
        resp = yield from self.make_request(
            'GET',
            self.build_url('folders', self.folder, 'items'),
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()

        ret = []
        for item in data['entries']:
            if item['type'] == 'folder':
                ret.append(BoxFolderMetadata(item, self.folder).serialized())
            else:
                ret.append(BoxFileMetadata(item, self.folder).serialized())
        return ret

    def _upload_create(self, stream, path):
        data_stream = streams.FormDataStream(
            attributes=json.dumps({'name': path.name, 'parent': {'id': path._id}}),
        )
        data_stream.add_file('file', stream, path.name, disposition='form-data')
        resp = yield from self.make_request(
            'POST',
            self._build_upload_url('files', 'content'),
            data=data_stream,
            headers=data_stream.headers,
            expects=(200, 201, ),
            throws=exceptions.UploadError,
        )
        data = yield from resp.json()
        return data

    def _upload_update(self, stream, path, meta):
        #'etag' of the file can be included as an ‘If-Match’ header to prevent race conditions
        meta_path = BoxPath(meta['path'])
        data_stream = streams.FormDataStream(
            attributes=json.dumps({'name': path.name, 'parent': {'id': path._id}}),
        )
        data_stream.add_file('file', stream, path.name, disposition='form-data')
        resp = yield from self.make_request(
            'POST',
            self._build_upload_url('files', meta_path._id, 'content'),
            data=data_stream,
            headers=data_stream.headers,
            expects=(200, 201, ),
            throws=exceptions.UploadError,
        )
        data = yield from resp.json()
        return data


    def _build_upload_url(self, *segments, **query): # ✓
        return provider.build_url(settings.BASE_UPLOAD_URL, *segments, **query)
