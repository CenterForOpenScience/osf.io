import os
import asyncio
from flask import request

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.gdrive import settings
from waterbutler.providers.gdrive.metadata import GoogleDriveRevision
from waterbutler.providers.gdrive.metadata import GoogleDriveFileMetadata
from waterbutler.providers.gdrive.metadata import GoogleDriveFolderMetadata




class GoogleDrivePath(utils.WaterButlerPath):

    def __init__(self, path, folder, prefix=True, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)

        parts = path.strip('/').split('/')
        name = parts[1]  # TODO : Remove this later if of no use
        folderId = parts[0]
        self._folderId = folderId
        if folderId == folder['id']:
            full_path = folder['name']
        else:
            tempPath = ''
            for i in range(2, len(parts)):
                if tempPath == '':
                    tempPath = parts[i]
                else:
                    tempPath = tempPath + '/' + parts[i]
            self._path = tempPath
            full_path = tempPath
        self._full_path = self._format_path(full_path)

    def __repr__(self):
        return "{}({!r}, {!r})".format(self.__class__.__name__, self._folderId, self._orig_path)

    @property
    def full_path(self):
        return self._full_path


class GoogleDriveProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL
    BASE_CONTENT_URL = settings.BASE_CONTENT_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.folder = self.settings['folder']

    @property
    def default_headers(self):
        return {
            'authorization': 'Bearer {}'.format(self.token),
        }

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):

        path = GoogleDrivePath(path, self.folder)
        import pdb; pdb.set_trace()
        resp = yield from self.make_request(
            'GET',
            self.build_url('files', path._folderId),
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        data = yield from resp.json()
        download_url = data['downloadUrl']
        downloadResp = yield from self.make_request(
            'GET',
            download_url,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        return streams.ResponseStreamReader(downloadResp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        path = path.get('id', path)
        try:
            yield from self.metadata(path)
        except exceptions.MetadataError:
            created = True
        else:
            created = False

        resp = yield from self.make_request(
            'POST',
            self._build_content_url('files', path, uploadType='media'),
            headers={'Content-Length': str(stream.size)
                     },
            data=stream,
            expects=(200, ),
            throws=exceptions.UploadError,
        )

        data = yield from resp.json()
        return GoogleDriveFileMetadata(data, self.folder).serialized(), created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        # A metadata call will verify the path specified is actually the
        # requested file or folder.
        yield from self.metadata(str(path))
        path = GoogleDrivePath(path, self.folder)
        yield from self.make_request(
            'DELETE',
            self.build_url('files', path._folderId),
            # data={'root': 'auto', 'path': path.full_path},
            expects=(200, 204),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        path = GoogleDrivePath(path, self.folder)

        resp = yield from self.make_request(
            'GET',
            self.build_url('files', q="'%s' in parents and trashed = false" % path._folderId, alt="json"),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from resp.json()
        if data['kind'] == "drive#fileList":
            ret = []
            for item in data['items']:
                item['path'] = os.path.join(path.full_path, item['title'])  # custom add, not obtained from API
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    ret.append(GoogleDriveFolderMetadata(item, self.folder).serialized())
                else:
                    ret.append(GoogleDriveFileMetadata(item, self.folder).serialized())
            return ret
        return GoogleDriveFileMetadata(data, self.folder).serialized()


    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        pass
        # path = DropboxPath(self.folder, path)
        # response = yield from self.make_request(
        #     'GET',
        #     self.build_url('revisions', 'auto', path.full_path),
        #     expects=(200, ),
        #     throws=exceptions.RevisionError
        # )
        # data = yield from response.json()
        #
        # return [
        #     DropboxRevision(item).serialized()
        #     for item in data
        # ]

    def _build_content_url(self, *segments, **query):
        return provider.build_url(settings.BASE_CONTENT_URL, *segments, **query)
