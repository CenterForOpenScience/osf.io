# encoding: utf-8

import os
import asyncio
from base64 import b64decode

import aiohttp

from tornado import web
from tornado.escape import json_decode

from webargs import Arg
from webargs.tornadoparser import use_kwargs

from waterbutler.providers.core import make_provider
from waterbutler.server import settings
from waterbutler.server.utils import coroutine


API_URL = 'http://localhost:5000/api/v1/files/auth/'


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        return value[0].decode('utf-8')
    return [item.decode('utf-8') for item in value]


def get_query_data(request):
    return {
        key: list_or_value(value)
        for key, value in request.items()
    }


@asyncio.coroutine
def fetch_identity(params):
    response = yield from aiohttp.request(
        'get',
        API_URL,
        params=params,
        headers={'Content-Type': 'application/json'},
    )

    # TOOD Handle Errors nicely
    if response.status != 200:
        data = yield from response.read()
        raise web.HTTPError(response.status)

    data = yield from response.json()
    return data


download_args = {
    'provider': Arg(str, use=lambda x: x.decode('utf-8'), required=True),
    'path': Arg(str, required=True),
}


class DownloadHandler(web.RequestHandler):

    @coroutine
    @use_kwargs(download_args)
    def get(self, provider, path):
        query = get_query_data(self.request.query_arguments)
        identity = yield from fetch_identity(query)
        provider = make_provider(provider, identity['identity'])
        response = yield from provider.download(**query)
        _, file_name = os.path.split(path)
        self.set_header('Content-Type', response.content_type)
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)
        while True:
            chunk = yield from response.content.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)

    def write_error(self, status_code, exc_info, **kwargs):
        self.set_status(status_code)
        # self.write(exc_info[1].message)
