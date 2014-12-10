# -*- coding: utf-8 -*-

import asyncio

import tornado.web

from waterbutler import exceptions
from waterbutler import settings
from waterbutler.identity import get_identity
from waterbutler.providers import core


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        return value[0].decode('utf-8')
    return [item.decode('utf-8') for item in value]


class BaseHandler(tornado.web.RequestHandler):

    ACTION_MAP = {}

    @asyncio.coroutine
    def prepare(self):
        self.arguments = {
            key: list_or_value(value)
            for key, value in self.request.query_arguments.items()
        }
        self.arguments['action'] = self.ACTION_MAP[self.request.method]

        self.credentials = yield from get_identity(settings.IDENTITY_METHOD, **self.arguments)

        self.provider = core.make_provider(
            self.arguments['provider'],
            self.credentials
        )

    def write_error(self, status_code, exc_info):
        etype, exc, _ = exc_info
        if etype is exceptions.WaterButlerError:
            if exc.data:
                self.finish(exc.data)
                return

        self.finish({
            "code": status_code,
            "message": self._reason,
        })
