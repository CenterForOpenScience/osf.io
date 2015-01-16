import asyncio
from unittest import mock

import pytest

from tests.utils import async

from waterbutler.core import utils


class TestAsyncRetry:

    @async
    def test_returns_success(self):
        mock_func = mock.Mock(return_value='Foo')
        retryable = utils.async_retry(5, 0)(mock_func)
        x = yield from retryable()
        assert x == 'Foo'
        assert mock_func.call_count == 1

    @async
    def test_retries_until(self):
        mock_func = mock.Mock(side_effect=[Exception(), 'Foo'])
        retryable = utils.async_retry(5, 0)(mock_func)

        first = yield from retryable()
        x = yield from first

        assert x == 'Foo'
        assert mock_func.call_count == 2

    @async
    def test_retries_then_raises(self):
        mock_func = mock.Mock(side_effect=Exception('Foo'))
        retryable = utils.async_retry(5, 0)(mock_func)

        coro = yield from retryable()

        with pytest.raises(Exception) as e:
            for _ in range(10):
                assert isinstance(coro, asyncio.Task)
                coro = yield from coro

        assert e.type == Exception
        assert e.value.args == ('Foo',)
        assert mock_func.call_count == 6

    @async
    def test_retries_by_its_self(self):
        mock_func = mock.Mock(side_effect=Exception())
        retryable = utils.async_retry(8, 0)(mock_func)

        coro = yield from retryable()

        yield from asyncio.sleep(2)

        assert mock_func.call_count == 9

    def test_docstring_survives(self):
        def mytest():
            '''This is a docstring'''
            pass

        retryable = utils.async_retry(8, 0)(mytest)

        assert retryable.__doc__ == '''This is a docstring'''
