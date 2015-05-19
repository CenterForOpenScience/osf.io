from tornado import web

from waterbutler.server import utils
from waterbutler.server import settings
from waterbutler.server.handlers import core


class ZipHandler(core.BaseHandler):

    ACTION_MAP = {
        'GET': 'zip',
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def get(self):
        """Download as a Zip archive."""

        self.set_header('Content-Type', 'application/zip')
        self.set_header(
            'Content-Disposition',
            utils.make_disposition('download.zip')
        )

        result = yield from self.provider.zip(**self.arguments)

        while True:
            chunk = yield from result.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)
            yield from utils.future_wrapper(self.flush())