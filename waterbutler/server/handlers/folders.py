import asyncio

from waterbutler.server import utils
from waterbutler.server.handlers import core


class FolderHandler(core.BaseHandler):

    ACTION_MAP = {
        'GET': 'create_folder',
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def get(self):
        """Create a folder"""
        self.set_status(201)
        self.write((yield from self.provider.create_folder(**self.arguments))
