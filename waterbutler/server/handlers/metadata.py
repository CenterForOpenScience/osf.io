# -*- coding: utf-8 -*-

import aiohttp

from waterbutler import settings
from waterbutler.providers import core
from waterbutler.server.utils import coroutine
from waterbutler.server.handlers import base


class MetadataHandler(base.ConvienceHandler):
    @coroutine
    def get(self):
        """List information about of file or folder"""
        result = yield from self.provider.metadata(**self.arguments)
        self.write({'data': result})
