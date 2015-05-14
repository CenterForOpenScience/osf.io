import asyncio
import os
import shutil
import tempfile
from unittest import mock

from decorator import decorator

import pytest
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


class TempFilesContext:
    def __init__(self):
        self._dir = tempfile.mkdtemp()
        self.files = []

    def add_file(self, filename=None):
        _, path = tempfile.mkstemp(dir=self._dir)

        if filename:
            os.rename(path, os.path.join(self._dir, filename))

        return path

    def tear_down(self):
        shutil.rmtree(self._dir)


@pytest.yield_fixture
def temp_files():
    context = TempFilesContext()
    yield context
    context.tear_down()