from waterbutler.server import utils
from waterbutler.server.handlers import core


class MetadataHandler(core.BaseHandler):

    ACTION_MAP = {
        'GET': 'metadata',
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def get(self):
        """List information about of file or folder"""
        result = yield from self.provider.metadata(**self.arguments)
        self.write({'data': result})
