# encoding: utf-8

from base64 import b64decode

from tornado import web
from tornado.escape import json_decode

from server import utils
from server import settings
from server.utils import coroutine


class DownloadHandler(web.RequestHandler):

    @coroutine
    def get(self):
        payload = json_decode(b64decode(self.get_argument('message')).decode('utf-8'))
        # signature = self.get_argument('signature')
        provider = utils.make_provider(payload['provider'])
        resp = yield from provider.download(**payload['options'])

        file_name = payload['options']['path'].split('/')[-1]
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)

        while True:
            chunk = yield from resp.content.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)
