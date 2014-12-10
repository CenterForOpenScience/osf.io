import asyncio

from waterbutler import settings


@asyncio.coroutine
def fetch_rest_identity(params):
    response = yield from aiohttp.request(
        'get',
        settings.IDENTITY_API_URL,
        params=params,
        headers={'Content-Type': 'application/json'},
    )

    # TOOD Handle Errors nicely
    if response.status != 200:
        data = yield from response.read()
        raise web.HTTPError(response.status)

    data = yield from response.json()
    return data

IDENTITY_METHODS = {
    'rest': fetch_rest_identity
}

get_identity = IDENTITY_METHODS[settings.IDENTITY_METHOD]
