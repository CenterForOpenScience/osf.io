import asyncio

from waterbutler.server import utils
from waterbutler.server.handlers import core


class RevisionHandler(core.BaseProviderHandler):

    ACTION_MAP = {
        'GET': 'revisions',
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def get(self):
        """List revisions of a file"""
        result = self.provider.revisions(**self.arguments)

        if asyncio.iscoroutine(result):
            result = yield from result

        self.write({'data': result})
