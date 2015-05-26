import asyncio
import aiohttp

from waterbutler.core import auth
from waterbutler.core import exceptions

from waterbutler.auth.osf import settings


class OsfAuthHandler(auth.BaseAuthHandler):
    """Identity lookup via the Open Science Framework"""

    @asyncio.coroutine
    def fetch(self, request, bundle):
        headers = {
            'Content-Type': 'application/json',
        }
        authorization = request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            headers['Authorization'] = authorization
        elif 'token' in bundle:
            headers['Authorization'] = 'Bearer ' + bundle['token']

        response = yield from aiohttp.request(
            'get',
            settings.API_URL,
            params=bundle,
            headers=headers
        )

        if response.status != 200:
            try:
                data = yield from response.json()
            except ValueError:
                data = yield from response.read()
            raise exceptions.AuthError(data, code=response.status)

        return (yield from response.json())
