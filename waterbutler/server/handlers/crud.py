import os
import http
import asyncio

from tornado import web

from waterbutler.core.streams import RequestStreamReader

from waterbutler.server import utils
from waterbutler.server import settings
from waterbutler.server.handlers import core
from waterbutler.core import exceptions


@web.stream_request_body
class CRUDHandler(core.BaseHandler):

    ACTION_MAP = {
        'GET': 'download',
        'PUT': 'upload',
        'DELETE': 'delete',
    }
    STREAM_METHODS = ('PUT', )

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()
        self.prepare_stream()

    def prepare_stream(self):
        if self.request.method in self.STREAM_METHODS:
            self.stream = RequestStreamReader(self.request)
            self.uploader = asyncio.async(
                self.provider.upload(self.stream, **self.arguments)
            )
        else:
            self.stream = None

    @utils.coroutine
    def data_received(self, chunk):
        """Note: Only called during uploads."""
        if self.stream:
            self.stream.feed_data(chunk)

    @utils.coroutine
    def get(self):
        """Download a file."""
        try:
            result = yield from self.provider.download(accept_url=True, **self.arguments)
        except exceptions.ProviderError as error:
            raise web.HTTPError(status_code=error.code)

        if isinstance(result, str):
            return self.redirect(result)

        display_name = self.arguments.get('displayName')
        if not display_name:
            _, display_name = os.path.split(self.arguments['path'])
        self.set_header('Content-Type', result.content_type)

        if result.size:
            self.set_header('Content-Length', str(result.size))
        self.set_header('Content-Disposition', 'attachment; filename=' + display_name)

        while True:
            chunk = yield from result.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)
            yield from utils.future_wrapper(self.flush())

    @utils.coroutine
    def put(self):
        """Upload a file."""
        self.stream.feed_eof()
        metadata, created = yield from self.uploader
        if created:
            self.set_status(201)
        self.write(metadata)

        self._send_hook(
            'create' if created else 'update',
            metadata,
        )

    @utils.coroutine
    def delete(self):
        """Delete a file."""
        # TODO: Current release does not allow deletion of directories (needs authorization code)
        if self.arguments.get('path', '').endswith('/'):
            raise web.HTTPError('Deletion of directories is currently not supported', status_code=400)

        yield from self.provider.delete(**self.arguments)
        self.set_status(http.client.NO_CONTENT)

        self._send_hook(
            'delete',
            {'path': self.arguments['path']}
        )
