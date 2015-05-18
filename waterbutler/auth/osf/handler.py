import asyncio
import aiohttp

from waterbutler.core import auth
from waterbutler.core import exceptions

from waterbutler.auth.osf import settings


class OsfAuthHandler(auth.BaseAuthHandler):
    """Identity lookup via the Open Science Framework"""

    @asyncio.coroutine
    def fetch(self, request_handler, **kwargs):
        headers = {
            'Content-Type': 'application/json',
        }
        authorization = request_handler.request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            headers['Authorization'] = authorization

        params = request_handler.arguments
        action = kwargs.get('action')
        if action:
            params['action'] = action
        provider = kwargs.get('provider')
        if provider:
            params['provider'] = provider

        response = yield from aiohttp.request(
            'get',
            settings.API_URL,
            params=params,
            headers=headers
        )
        if response.status != 200:
            try:
                data = yield from response.json()
            except ValueError:
                data = yield from response.read()
            raise exceptions.AuthError(data, code=response.status)
        data = yield from response.json()
        return data
