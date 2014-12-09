# -*- coding: utf-8 -*-

import os
import asyncio
from base64 import b64decode

import aiohttp

from tornado import web, gen
from tornado.escape import json_decode

from webargs import Arg
from webargs.tornadoparser import use_kwargs

from waterbutler.server import settings

from waterbutler.providers import core
from waterbutler.server import utils
from waterbutler.server.utils import coroutine


API_URL = 'http://localhost:5000/api/v1/files/auth/'

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


upload_args = {
    'provider': Arg(str, required=True, use=lambda v: v.decode('utf-8')),
    'path': Arg(str, required=True, use=lambda v: v.decode('utf-8')),
}


STREAM_METHODS = ('PUT', 'POST')

ACTION_MAP = {
    'GET': 'download',
    'PUT': 'upload',
    'DELETE': 'delete',
}


@web.stream_request_body
class CRUDHandler(web.RequestHandler):

    @coroutine
    @use_kwargs(upload_args)
    def prepare(self, provider, path):
        self.arguments = get_query_data(self.request.query_arguments)
        self.arguments['action'] = ACTION_MAP[self.request.method]
        self.credentials = yield from fetch_identity(self.arguments)
        self.provider = core.make_provider(provider, self.credentials)
        self.prepare_stream()

    def prepare_stream(self):
        if self.request.method in STREAM_METHODS:
            self.obj = core.RequestWrapper(self.request)
            self.uploader = self.provider.upload(self.obj, **self.arguments)
        else:
            self.obj = None

    def data_received(self, chunk):
        """Note: Only called during uploads."""
        if self.obj:
            self.obj.content.feed_data(chunk)

    @coroutine
    def get(self):
        """Download a file."""
        result = yield from self.provider.download(**self.arguments)
        _, file_name = os.path.split(self.arguments['path'])
        self.set_header('Content-Type', result.content_type)
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)
        while True:
            chunk = yield from result.content.read(settings.CHUNK_SIZE)
            if not chunk:
                break
            self.write(chunk)

    @coroutine
    def put(self):
        """Upload a file."""
        self.obj.content.feed_eof()
        result = yield from self.uploader
        self.set_status(result.response.status)

    @coroutine
    def delete(self):
        """Delete a file."""
        result = yield from self.provider.delete(**self.arguments)
        self.set_status(result.response.status)

    def on_connection_close(self):
        if self.request.method in STREAM_METHODS:
            self.obj.content.feed_eof()
