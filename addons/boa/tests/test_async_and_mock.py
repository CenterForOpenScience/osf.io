import asynctest
import mock
import pytest
import unittest

from addons.boa.async_and_mock import foo_sync, bar_async, bar_async_to_sync
from addons.boa.tests.async_mock import AsyncMock


def test_foo_sync():
    r = foo_sync(True, True)
    assert r is True, 'test failed'


@mock.patch('addons.boa.async_and_mock.just_return_1')
@mock.patch('addons.boa.async_and_mock.just_return_2')
def test_foo_sync_with_mock_via_decorator(mock_just_return_2, mock_just_return_1):
    mock_just_return_1.return_value = True
    mock_just_return_2.return_value = False
    r = foo_sync(True, True)
    mock_just_return_1.assert_called()
    mock_just_return_2.assert_called()
    assert r is False, 'test failed'


def test_foo_sync_with_mock_in_context():
    with mock.patch('addons.boa.async_and_mock.just_return_1', return_value=True) as mock_just_return_1, \
            mock.patch('addons.boa.async_and_mock.just_return_2', return_value=False) as mock_just_return_2:
        r = foo_sync(True, True)
        mock_just_return_1.assert_called()
        mock_just_return_2.assert_called()
        assert r is False, 'test failed'


@pytest.mark.asyncio
async def test_bar_async():
    r = await bar_async(True, True)
    assert r is True, 'test failed'


# Note: this test demonstrates that decorator @pytest.mark.asyncio breaks @mock.patch()!!!
@pytest.mark.asyncio
@mock.patch('addons.boa.async_and_mock.just_return_1')
@mock.patch('addons.boa.async_and_mock.just_return_2')
async def test_bar_async_with_mock_via_decorator(mock_just_return_2, mock_just_return_1):
    mock_just_return_1.return_value = True
    mock_just_return_2.return_value = False
    r = await bar_async(True, True)
    mock_just_return_1.assert_not_called()
    mock_just_return_2.assert_not_called()
    assert r is True, 'test failed'


# Note: this test demonstrates that ``with mock.patch()`` context is compatible with decorator @pytest.mark.asyncio.
@pytest.mark.asyncio
async def test_bar_async_with_mock():
    with mock.patch('addons.boa.async_and_mock.just_return_1', return_value=True) as mock_just_return_1,\
            mock.patch('addons.boa.async_and_mock.just_return_2', return_value=False) as mock_just_return_2:
        r = await bar_async(True, True)
        mock_just_return_1.assert_called()
        mock_just_return_2.assert_called()
        assert r is False, 'test failed'


# Note: this test demonstrates how to patch an async function/method.
@mock.patch('addons.boa.async_and_mock.bar_async', new_callable=AsyncMock, return_value=False)
def test_bar_async_to_sync(mock_bar_async):
    r = bar_async_to_sync(True, True)
    mock_bar_async.assert_called()
    assert r is False


# Note: this class demonstrates that decorator ``@pytest.mark.asyncio`` does not work with subclasses of
# ``unittest.TestCase``; ``test_bar_async`` will not be waited and always passes even with ``assert False``
# since the decorator is ignored.
class TestAsyncFunctionWithSubclassingTestCase(unittest.TestCase):
    @pytest.mark.asyncio
    async def test_bar_async(self):
        r = await bar_async(True, True)
        assert r is True, 'test failed'
        assert False


# Note: use ``asynctest.TestCase`` instead
class TestAsyncFunctionWithSubclassingAsyncTestCase(asynctest.TestCase):
    @pytest.mark.xfail
    async def test_bar_async(self):
        r = await bar_async(True, True)
        assert r is True, 'test failed'
        assert False
