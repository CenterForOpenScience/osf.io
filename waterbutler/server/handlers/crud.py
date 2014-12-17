import os
import asyncio

from tornado import web

from waterbutler import settings
from waterbutler.streams import RequestStreamReader
from waterbutler.server import utils
from waterbutler.server.handlers import core


loop = asyncio.get_event_loop()

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

    # @asyncio.coroutine
    def prepare_stream(self):
        if self.request.method in self.STREAM_METHODS:
            self.stream = RequestStreamReader(self.request)
            self.uploader = asyncio.async(self.provider.upload(self.stream, **self.arguments))
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
        result = yield from self.provider.download(accept_url=True, **self.arguments)

        if isinstance(result, str):
            return self.redirect(result)

        _, file_name = os.path.split(self.arguments['path'])
        self.set_header('Content-Type', result.content_type)

        if result.size:
            self.set_header('Content-Length', str(result.size))
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)

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
        result = yield from self.uploader
        self.write(result)

    @utils.coroutine
    def delete(self):
        """Delete a file."""
        yield from self.provider.delete(**self.arguments)
        self.set_status(204)

    def on_connection_close(self):
        if self.request.method in self.STREAM_METHODS:
            try:
                self.stream.feed_eof()
            except AttributeError:
                pass
