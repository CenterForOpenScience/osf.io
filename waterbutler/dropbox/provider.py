import re
import os
import asyncio

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.dropbox import settings
from waterbutler.dropbox.metadata import DropboxRevision
from waterbutler.dropbox.metadata import DropboxFileMetadata
from waterbutler.dropbox.metadata import DropboxFolderMetadata


# TODO Test this and make sure .. doesn't work
def guarded(func):
    def wrapped(self, path, *args, **kwargs):
        stripped = re.sub('^{}/?'.format(re.escape(self.folder)), '', path)
        if stripped == path:
            raise exceptions.MetadataError('Root folder not present in path')
        return func(self, path, *args, **kwargs)
    return func


class DropboxProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL
    BASE_CONTENT_URL = settings.BASE_CONTENT_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.folder = self.settings['folder']

    def build_content_url(self, *segments, **query):
        return provider.build_url(settings.BASE_CONTENT_URL, *segments, **query)

    def build_path(self, path):
        return os.path.join(self.folder, path.strip('/'))

    @property
    def default_headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token),
        }

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return self.can_intra_copy(dest_provider)

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        from_path = self.build_path(source_options['path'])
        to_path = self.build_path(dest_options['path'])
        if self == dest_provider:
            resp = yield from self.make_request(
                'POST',
                self.build_url('fileops', 'copy'),
                data={
                    'folder': 'auto',
                    'from_path': from_path,
                    'to_path': to_path,
                },
                expects=(200, 201),
                throws=exceptions.IntraCopyError,
            )
        else:
            from_ref_resp = yield from self.make_request(
                'GET',
                self.build_url('copy_ref', 'auto', from_path),
            )
            from_ref_data = yield from from_ref_resp.json()
            resp = yield from self.make_request(
                'POST',
                data={
                    'root': 'auto',
                    'from_copy_ref': from_ref_data['copy_ref'],
                    'to_path': to_path,
                },
                headers=dest_provider.default_headers,
                expects=(200, 201),
                throws=exceptions.IntraCopyError,
            )
        data = yield from resp.json()
        return DropboxFileMetadata(data).serialized()

    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        from_path = self.build_path(source_options['path'])
        to_path = self.build_path(dest_options['path'])
        resp = yield from self.make_request(
            'POST',
            self.build_url('fileops', 'move'),
            data={
                'root': 'auto',
                'from_path': from_path,
                'to_path': to_path,
            },
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )
        data = yield from resp.json()
        return DropboxFileMetadata(data).serialized()

    @guarded
    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_content_url('files', 'auto', self.build_path(path)),
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @guarded
    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        try:
            yield from self.metadata(path)
        except exceptions.MetadataError:
            created = True
        else:
            created = False

        resp = yield from self.make_request(
            'PUT',
            self.build_content_url('files_put', 'auto', self.build_path(path)),
            headers={'Content-Length': str(stream.size)},
            data=stream,
            expects=(200, ),
            throws=exceptions.UploadError,
        )

        data = yield from resp.json()
        return DropboxFileMetadata(data).serialized(), created

    @guarded
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        yield from self.make_request(
            'POST',
            self.build_url('fileops', 'delete'),
            data={'root': 'auto', 'path': self.build_path(path)},
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @guarded
    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_url('metadata', 'auto', self.build_path(path)),
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from response.json()

        if data['is_dir']:
            ret = []
            for item in data['contents']:
                if item['is_dir']:
                    ret.append(DropboxFolderMetadata(item).serialized())
                else:
                    ret.append(DropboxFileMetadata(item).serialized())
            return ret

        return DropboxFileMetadata(data).serialized()

    @guarded
    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_url('revisions', 'auto', self.build_path(path)),
            expects=(200, ),
            throws=exceptions.RevisionError
        )

        data = yield from response.json()

        return [
            DropboxRevision(item).serialized()
            for item in data
        ]
