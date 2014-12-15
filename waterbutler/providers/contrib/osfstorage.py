import os
import uuid
import asyncio
import hashlib

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions


@core.register_provider('osfstorage')
class OSFStorageProvider(core.BaseProvider):

    FILE_PATH_PENDING = '/tmp/pending'
    FILE_PATH_COMPLETE = '/tmp/complete'

    def __init__(self, auth, identity):
        super().__init__(auth, identity)
        self.provider = core.make_provider(identity['provider'], auth=auth, identity=identity)

    @asyncio.coroutine
    def download(self, path, **kwargs):
        # osf storage metadata will return a virtual path within the provider
        resp = yield from self.make_request(
            'GET',
            self.identity['crudCallback'],
            params=kwargs,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        data = yield from resp.json()
        return (yield from self.provider.download(**data))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        pending_name = uuid.uuid4()
        pending_path = '/tmp/pending/{}'.format(pending_name)
        stream.add_writer('sha256', streams.HashStreamWriter(hashlib.sha256))
        stream.add_writer('file', open(pending_path, 'wb'))
        resp = yield from self.make_request(
            'PUT',
            self.build_content_url('files_put', 'auto', self.build_path(path)),
            headers={'Content-Length': str(stream.size)},
            data=stream,
            expects=(200, ),
            throws=exceptions.UploadError,
        )
        complete_name = stream.streams['sha256'].hexdigest
        complete_path = '/tmp/complete/{}'.format(complete_name)
        yield from self.provider.move(
            self.provider,
            {'path': pending_name},
            {'path': complete_name}
        )
        os.rename(pending_path, complete_path)
        yield from self.make_request(
            'PUT',
            self.identity['crudCallback'],
            data={
                '...auth..provider metadata...hashes...nid, virtual_path': '...'
            }
        )
        # TODO: Celery Tasks for Parity & Archive
        # tasks.Archive()
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        # resp = yield from self.make_request(
        #     'DELETE',
        #     self.identity['crudCallback'],
        #     params=kwargs,
        # )
        pass
        # # call to osf metadata
        # response = yield from self.make_request(
        #     'POST',
        #     self.build_url('fileops', 'delete'),
        #     data={'folder': 'auto', 'path': self.build_path(path)},
        # )
        # return streams.ResponseStream(response)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.identity['metadataCallback'],
            params=kwargs
        )
        # response = yield from self.make_request(
        #     'GET',
        #     self.build_url('metadata', 'auto', self.build_path(path)),
        # )
        # if response.status != 200:
        #     raise exceptions.FileNotFoundError(path)
        #
        data = yield from resp.json()
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
