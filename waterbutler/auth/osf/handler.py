import asyncio
import aiohttp

from waterbutler.core import auth
from waterbutler.core import exceptions

from waterbutler.auth.osf import settings


class OsfAuthHandler(auth.BaseAuthHandler):
    """Identity lookup via the Open Science Framework"""

    @asyncio.coroutine
    def fetch(self, request_handler):
        headers= {
            'Content-Type': 'application/json',
        }
        authorization = request_handler.request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            headers['Authorization'] = authorization
        response = yield from aiohttp.request(
            'get',
            settings.API_URL,
            params=request_handler.arguments,
            headers={
                'Authorization': authorization,
                'Content-Type': 'application/json'
            },
        )
        if response.status != 200:
            try:
                data = yield from response.json()
            except ValueError:
                data = yield from response.read()
            raise exceptions.AuthError(data, code=response.status)
        data = yield from response.json()
        return data
