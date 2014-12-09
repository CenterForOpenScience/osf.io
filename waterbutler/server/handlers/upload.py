# encoding: utf-8

import asyncio

from base64 import b64decode

from tornado import web
from tornado.escape import json_decode

from waterbutler.providers.core import make_provider
from waterbutler.providers.core import RequestWrapper
from waterbutler.server import utils
from waterbutler.server.utils import coroutine


@web.stream_request_body
class UploadHandler(web.RequestHandler):

    @coroutine
    def prepare(self):
        self.payload = json_decode(b64decode(self.get_argument('message')).decode('utf-8'))
        # self.signature = self.get_argument('signature')
        self.provider = make_provider(self.payload['provider'])

        self.obj = RequestWrapper(self.request)
        self.uploader = asyncio.async(self.provider.upload(self.obj, self.payload['options']['path']))

    def data_received(self, chunk):
        self.obj.content.feed_data(chunk)

    @coroutine
    def put(self):
        self.obj.content.feed_eof()
        result = yield from self.uploader
        self.set_status(result.response.status)

    def on_connection_close(self, *args, **kwargs):
        self.obj.content.feed_eof()
