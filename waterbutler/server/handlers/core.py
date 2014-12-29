import json
import time
import asyncio

import aiohttp
import tornado.web

from stevedore import driver

from waterbutler.core import signing
from waterbutler.core import exceptions

from waterbutler.server import settings
from waterbutler.server.identity import get_identity


CORS_ACCEPT_HEADERS = [
    'Content-Type',
    'Cache-Control',
    'X-Requested-With',
]


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        # Remove leading slashes as they break things
        return value[0].decode('utf-8')
    return [item.decode('utf-8') for item in value]


def make_provider(name, auth, credentials, settings):
    manager = driver.DriverManager(
        namespace='waterbutler.providers',
        name=name,
        invoke_on_load=True,
        invoke_args=(auth, credentials, settings),
    )
    return manager.driver


signer = signing.Signer(settings.HMAC_SECRET, settings.HMAC_ALGORITHM)


class BaseHandler(tornado.web.RequestHandler):

    ACTION_MAP = {}

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

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

        self.provider = make_provider(
            self.arguments['provider'],
            self.payload['auth'],
            self.payload['credentials'],
            self.payload['settings'],
        )

    def write_error(self, status_code, exc_info):
        etype, exc, _ = exc_info
        if issubclass(etype, exceptions.ProviderError):
            if exc.data:
                self.set_status(exc.code)
                self.finish(exc.data)
                return

        self.finish({
            "code": status_code,
            "message": self._reason,
        })

    def options(self):
        self.set_status(204)
        self.set_header('Access-Control-Allow-Methods', 'PUT, DELETE'),
        self.set_header('Access-Control-Allow-Headers', ', '.join(CORS_ACCEPT_HEADERS))

    @asyncio.coroutine
    def _send_hook(self, action, metadata):
        payload = {
            'action': action,
            'provider': self.arguments['provider'],
            'metadata': metadata,
            'auth': self.payload['auth'],
            'time': time.time() + 60
        }
        message, signature = signer.sign_payload(payload)
        resp = aiohttp.request(
            'PUT',
            self.payload['callback_url'],
            data=json.dumps({
                'payload': message.decode(),
                'signature': signature,
            }),
            headers={'Content-Type': 'application/json'},
        )
        return resp
