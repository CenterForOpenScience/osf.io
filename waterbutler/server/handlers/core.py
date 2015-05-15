import json
import time
import asyncio

import tornado.web
from raven.contrib.tornado import SentryMixin

from waterbutler import tasks
from waterbutler.core import utils
from waterbutler.core import signing
from waterbutler.core import exceptions
from waterbutler.server import settings
from waterbutler.server.identity import get_identity


CORS_ACCEPT_HEADERS = [
    'Range',
    'Content-Type',
    'Cache-Control',
    'X-Requested-With',
]

CORS_EXPOSE_HEADERS = [
    'Accept-Ranges',
    'Content-Range',
    'Content-Length',
    'Content-Encoding',
]

HTTP_REASONS = {
    422: 'Unprocessable Entity',
    461: 'Unavailable For Legal Reasons',
}


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        # Remove leading slashes as they break things
        return value[0].decode('utf-8')
    return [item.decode('utf-8') for item in value]


signer = signing.Signer(settings.HMAC_SECRET, settings.HMAC_ALGORITHM)


class BaseHandler(tornado.web.RequestHandler, SentryMixin):
    """Base Handler to inherit from when defining a new view.
    Handles CORs headers, additional status codes, and translating
    :class:`waterbutler.core.exceptions.ProviderError`s into http responses

    .. note::
        For IE compatability passing a ?method=<httpmethod> will cause that request, regardless of the
        actual method, to be interpreted as the specified method.
    """

    ACTION_MAP = {}

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', settings.CORS_ALLOW_ORIGIN)
        self.set_header('Access-Control-Allow-Headers', ', '.join(CORS_ACCEPT_HEADERS))
        self.set_header('Access-Control-Expose-Headers', ', '.join(CORS_EXPOSE_HEADERS))
        self.set_header('Cache-control', 'no-store, no-cache, must-revalidate, max-age=0')

    def initialize(self):
        method = self.get_query_argument('method', None)
        if method:
            self.request.method = method.upper()

    def set_status(self, code, reason=None):
        return super().set_status(code, reason or HTTP_REASONS.get(code))

    def write_error(self, status_code, exc_info):
        self.captureException(exc_info)
        etype, exc, _ = exc_info

        if issubclass(etype, exceptions.ProviderError):
            self.set_status(exc.code)
            if exc.data:
                self.finish(exc.data)
            else:
                self.finish({
                    'code': exc.code,
                    'message': exc.message
                })

        elif issubclass(etype, tasks.WaitTimeOutError):
            # TODO
            self.set_status(202)
        else:
            self.finish({
                'code': status_code,
                'message': self._reason,
            })

    def options(self):
        self.set_status(204)
        self.set_header('Access-Control-Allow-Methods', 'PUT, POST, DELETE'),


class BaseProviderHandler(BaseHandler):

    @asyncio.coroutine
    def prepare(self):
        self.arguments = {
            key: list_or_value(value)
            for key, value in self.request.query_arguments.items()
        }
        try:
            self.arguments['action'] = self.ACTION_MAP[self.request.method]
        except KeyError:
            return

        self.payload = yield from get_identity(settings.IDENTITY_METHOD, **self.arguments)

        self.provider = utils.make_provider(
            self.arguments['provider'],
            self.payload['auth'],
            self.payload['credentials'],
            self.payload['settings'],
        )

        self.path = yield from self.provider.validate_path(**self.arguments)
        self.arguments['path'] = self.path  # TODO Not this

    @utils.async_retry(retries=5, backoff=5)
    def _send_hook(self, action, metadata):
        return (yield from utils.send_signed_request('PUT', self.payload['callback_url'], {
            'action': action,
            'metadata': metadata,
            'auth': self.payload['auth'],
            'provider': self.arguments['provider'],
            'time': time.time() + 60
        }))


class BaseCrossProviderHandler(BaseHandler):
    JSON_REQUIRED = False

    @asyncio.coroutine
    def prepare(self):
        try:
            self.action = self.ACTION_MAP[self.request.method]
        except KeyError:
            return

        self.source_provider = yield from self.make_provider(**self.json['source'])
        self.destination_provider = yield from self.make_provider(**self.json['destination'])

        self.json['source']['path'] = yield from self.source_provider.validate_path(**self.json['source'])
        self.json['destination']['path'] = yield from self.destination_provider.validate_path(**self.json['destination'])

    @asyncio.coroutine
    def make_provider(self, provider, **kwargs):
        payload = yield from get_identity(
            settings.IDENTITY_METHOD,
            action=self.ACTION_MAP[self.request.method],
            provider=provider,
            **kwargs
        )
        self.auth = payload
        self.callback_url = payload.pop('callback_url')
        return utils.make_provider(provider, **payload)

    @property
    def json(self):
        try:
            return self._json
        except AttributeError:
            pass
        try:
            self._json = json.loads(self.request.body.decode('utf-8'))
        except ValueError:
            if self.JSON_REQUIRED:
                raise Exception  # TODO
            self._json = None

        return self._json

    @utils.async_retry(retries=0, backoff=5)
    def _send_hook(self, action, data):
        return (yield from utils.send_signed_request('PUT', self.callback_url, {
            'action': action,
            'source': {
                'provider': self.source_provider.NAME,
                'path': self.json['source']['path'].path,
                'name': self.json['source']['path'].name,
                'materialized': str(self.json['source']['path']),
            },
            'destination': data,
            'auth': self.auth['auth'],
            'time': time.time() + 60
        }))
