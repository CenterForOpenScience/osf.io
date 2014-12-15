import os
import asyncio

from waterbutler import exceptions
from waterbutler.providers import core


@core.register_provider('dropbox')
class DropboxProvider(core.BaseProvider):

    BASE_URL = 'https://api.dropbox.com/1/'
    BASE_CONTENT_URL = 'https://api-content.dropbox.com/1/'

    def __init__(self, auth, identity):
        super().__init__(auth, identity)
        self.folder = self.identity['folder']
        self.token = self.identity['token']

    def build_content_url(self, *segments, **query):
        return core.build_url(self.BASE_CONTENT_URL, *segments, **query)

    def build_path(self, path):
        return os.path.join(self.folder, path)

    @property
    def default_headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token),
        }

    def __eq__(self, other):
        try:
            return (
                type(self) == type(other) and
                self.identity == other.identity
            )
        except AttributeError:
            return False

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return self == dest_provider

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        from_path = self.build_path(source_options['path'])
        to_path = self.build_path(dest_options['path'])
        if self == dest_provider:
            response = yield from self.make_request(
                'POST',
                self.build_url('fileops', 'copy'),
                data={
                    'folder': 'auto',
                    'from_path': from_path,
                    'to_path': to_path,
                },
            )
        else:
            from_ref_resp = yield from self.make_request(
                'GET',
                self.build_url('copy_ref', 'auto', from_path),
            )
            from_ref_data = yield from from_ref_resp.json()
            response = yield from self.make_request(
                'POST',
                data={
                    'folder': 'auto',
                    'from_copy_ref': from_ref_data['copy_ref'],
                    'to_path': to_path,
                },
                headers=dest_provider.default_headers,
            )
        return core.ResponseStreamReader(response)

    @core.expects(200)
    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        from_path = self.build_path(source_options['path'])
        to_path = self.build_path(dest_options['path'])
        response = yield from self.make_request(
            'POST',
            self.build_url('fileops', 'move'),
            data={
                'folder': 'auto',
                'from_path': from_path,
                'to_path': to_path,
            },
        )
        return core.ResponseStreamReader(response)

    @core.expects(200)
    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_content_url('files', 'auto', self.build_path(path)),
        )
        return core.ResponseStreamReader(resp)

    @core.expects(200)
    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        resp = yield from self.make_request(
            'PUT',
            self.build_content_url('files_put', 'auto', self.build_path(path)),
            headers={'Content-Length': str(stream.size)},
            data=stream,
        )
        return core.ResponseStreamReader(resp)

    @core.expects(200)
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        response = yield from self.make_request(
            'POST',
            self.build_url('fileops', 'delete'),
            data={'folder': 'auto', 'path': self.build_path(path)},
        )
        return core.ResponseStreamReader(response)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_url('metadata', 'auto', self.build_path(path)),
        )
        if response.status != 200:
            raise exceptions.FileNotFoundError(path)

        data = yield from response.json()
        return [self.format_metadata(x) for x in data]

    def format_metadata(self, data):
        return {
            'provider': 'dropbox',
            'kind': 'folder' if data['is_dir'] else 'file',
            'name': os.path.split(data['path'])[1],
            'path': data['path'],
            'size': data['bytes'],
            'modified': data['modified'],
            'extra': {}  # TODO Include extra data from dropbox
        }
