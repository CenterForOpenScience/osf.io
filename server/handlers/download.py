# encoding: utf-8

from tornado import web
from tornado.escape import json_decode

from server import utils
from server import settings
from server.utils import coroutine


class DownloadHandler(web.RequestHandler):

    @coroutine
    def get(self):
        payload = json_decode(self.get_argument('message'))
        provider_info = payload['provider']
        options = payload['options']
        provider = utils.make_provider(provider_info)
        resp = yield from provider.download(**options)

        while True:
            chunk = yield from resp.content.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)
