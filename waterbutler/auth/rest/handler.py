import asyncio
import aiohttp

from waterbutler.core import auth
from waterbutler.core import exceptions

from waterbutler.auth.rest import settings


class RestAuthHandler(auth.BaseAuthHandler):
    """Identity lookup by Restful HTTP Request"""

    @asyncio.coroutine
    def fetch(self, request_handler):
        response = yield from aiohttp.request(
            'get',
            settings.API_URL,
            params=request_handler.arguments,
            headers={'Content-Type': 'application/json'},
        )
        if response.status != 200:
            try:
                data = yield from response.json()
            except ValueError:
                data = yield from response.read()
            raise exceptions.AuthError(data, code=response.status)
        data = yield from response.json()
        return data
