import pytest
import random
import string
import functools
from unittest import mock

from tests.utils import async

from waterbutler.core import streams


@pytest.fixture
def blob():
    return ''.join(random.sample(string.printable, 50)).encode('utf-8')


class TestMultiStream:

    @async
    def test_single_stream(self, blob):
        stream = streams.MultiStream(streams.StringStream(blob))
        data = yield from stream.read()
        assert data == blob

    @async
    def test_double_same_stream(self, blob):
        stream = streams.MultiStream(
            streams.StringStream(blob),
            streams.StringStream(blob)
        )
        data = yield from stream.read()
        assert data == (blob * 2)

    @async
    def test_1_at_a_time_single_stream(self, blob):
        stream = streams.MultiStream(streams.StringStream(blob))
        for i in range(len(blob)):
            assert blob[i:i + 1] == (yield from stream.read(1))

    @async
    def test_1_at_a_time_many_stream(self, blob):
        count = 4
        stream = streams.MultiStream(*[streams.StringStream(blob) for _ in range(count)])

        for _ in range(count):
            for i in range(len(blob)):
                assert blob[i:i + 1] == (yield from stream.read(1))
