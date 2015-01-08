import asyncio

import aiohttp

from tornado.options import options

from waterbutler.server import exceptions


IDENTITY_METHODS = {}


def get_identity_func(name):
    try:
        return IDENTITY_METHODS[name]
    except KeyError:
        raise NotImplementedError('No identity getter for {0}'.format(name))


def register_identity(name):
    def _register_identity(func):
        IDENTITY_METHODS[name] = func
        return func
    return _register_identity


def get_identity(name, **kwargs):
    return get_identity_func(name)(**kwargs)


@register_identity('rest')
@asyncio.coroutine
def fetch_rest_identity(**params):
    response = yield from aiohttp.request(
        'get',
        options.identity_api_url,
        params=params,
        headers={'Content-Type': 'application/json'},
    )

    # TOOD Handle Errors nicely
    if response.status != 200:
        try:
            data = yield from response.json()
        except ValueError:
            data = yield from response.read()

        raise exceptions.WaterButlerError(data, code=response.status)

    data = yield from response.json()
    return data
