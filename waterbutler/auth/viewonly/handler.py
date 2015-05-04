import asyncio
import aiohttp

from waterbutler.core import auth
from waterbutler.core import exceptions

from waterbutler.auth.viewonly import settings


class ViewOnlyAuthHandler(auth.BaseAuthHandler):
    """Authentication Credential lookup by view only api key"""

    @asyncio.coroutine
    def fetch(self, request_handler):
        view_only = request_handler.arguments.get(settings.URL_PARAMETER_NAME)
        if not view_only:
            return
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
