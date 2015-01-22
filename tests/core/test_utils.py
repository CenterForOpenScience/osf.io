import asyncio
from unittest import mock

import pytest

from tests.utils import async

from waterbutler.core import utils


class TestAsyncRetry:

    @async
    def test_returns_success(self):
        mock_func = mock.Mock(return_value='Foo')
        retryable = utils.async_retry(5, 0, raven=None)(mock_func)
        x = yield from retryable()
        assert x == 'Foo'
        assert mock_func.call_count == 1

    @async
    def test_retries_until(self):
        mock_func = mock.Mock(side_effect=[Exception(), 'Foo'])
        retryable = utils.async_retry(5, 0, raven=None)(mock_func)

        first = yield from retryable()
        x = yield from first

        assert x == 'Foo'
        assert mock_func.call_count == 2

    @async
    def test_retries_then_raises(self):
        mock_func = mock.Mock(side_effect=Exception('Foo'))
        retryable = utils.async_retry(5, 0, raven=None)(mock_func)

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
        retryable = utils.async_retry(8, 0, raven=None)(mock_func)

        retryable()

        yield from asyncio.sleep(.1)

        assert mock_func.call_count == 9

    def test_docstring_survives(self):
        def mytest():
            '''This is a docstring'''
            pass

        retryable = utils.async_retry(8, 0, raven=None)(mytest)

        assert retryable.__doc__ == '''This is a docstring'''

    @async
    def test_kwargs_work(self):
        def mytest(mack, *args, **kwargs):
            mack()
            assert args == ('test', 'Foo')
            assert kwargs == {'test': 'Foo', 'baz': 'bam'}
            return True

        retryable = utils.async_retry(8, 0, raven=None)(mytest)
        merk = mock.Mock(side_effect=[Exception(''), 5])

        fut = retryable(merk, 'test', 'Foo', test='Foo', baz='bam')
        assert (yield from (yield from fut))

        assert merk.call_count == 2

    @async
    def test_all_retry(self):
        mock_func = mock.Mock(side_effect=Exception())
        retryable = utils.async_retry(8, 0, raven=None)(mock_func)

        retryable()
        retryable()

        yield from asyncio.sleep(.1)

        assert mock_func.call_count == 18
