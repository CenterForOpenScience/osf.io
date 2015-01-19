import asyncio
from unittest import mock

from decorator import decorator

from tornado import testing
from tornado.platform.asyncio import AsyncIOMainLoop

from waterbutler.server.app import make_app


@decorator
def async(func, *args, **kwargs):
    future = func(*args, **kwargs)
    asyncio.get_event_loop().run_until_complete(future)


class HandlerTestCase(testing.AsyncHTTPTestCase):

    def get_app(self):
        return make_app(debug=False)

    def get_new_ioloop(self):
        return AsyncIOMainLoop()


def mock_provider_method(mock_make_provider, method_name, return_value=None,
                         side_effect=None, as_coro=True):
    mock_provider = mock.Mock()
    method = getattr(mock_provider, method_name)
    coro = asyncio.coroutine(lambda: return_value)
    method.return_value = coro() if as_coro else return_value
    if side_effect:
        method.side_effect = side_effect
    mock_make_provider.return_value = mock_provider
    return mock_provider
