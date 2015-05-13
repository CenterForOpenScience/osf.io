import asyncio
from unittest import mock

from decorator import decorator

from tornado import testing
from tornado.platform.asyncio import AsyncIOMainLoop

from waterbutler.core import provider
from waterbutler.server.app import make_app
from waterbutler.core.path import WaterButlerPath


class MockCoroutine(mock.Mock):
    @asyncio.coroutine
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

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


class MockProvider1(provider.BaseProvider):

    NAME = 'MockProvider1'

    @asyncio.coroutine
    def validate_path(self, path, **kwargs):
        return WaterButlerPath(path)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        return {}, True

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        pass

    @asyncio.coroutine
    def metadata(self, path, throw=None, **kwargs):
        if throw:
            raise throw
        return {}

    @asyncio.coroutine
    def download(self, path):
        return b''

class MockProvider2(MockProvider1):

    NAME = 'MockProvider2'

    def can_intra_move(self, other, path=None):
        return self.__class__ == other.__class__

    def can_intra_copy(self, other, path=None):
        return self.__class__ == other.__class__
