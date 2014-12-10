# -*- coding: utf-8 -*-

import aiohttp

from waterbutler.server.handlers import core
from waterbutler.server.utils import coroutine


class MetadataHandler(core.BaseHandler):
    @coroutine
    def get(self):
        """List information about of file or folder"""
        result = yield from self.provider.metadata(**self.arguments)
        self.write({'data': result})
