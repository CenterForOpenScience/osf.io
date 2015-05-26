import pytest
import base64
import functools
from unittest import mock

from tests.utils import async

from waterbutler.core import streams


class TestBase64Stream:

    @async
    def test_doesnt_crash_with_none(self):
        stream = streams.Base64EncodeStream(streams.StringStream(b''))
        data = yield from stream.read()

        assert data == b''

    @async
    def test_read(self):
        data = b'this is a test'
        expected = base64.b64encode(data)
        stream = streams.Base64EncodeStream(streams.StringStream(data))

        actual = yield from stream.read()

        assert expected == actual

    @async
    def test_chunking(self):
        for chunk_size in range(1, 10):
            data = b'the ode to carp'
            expected = streams.StringStream(base64.b64encode(data))
            stream = streams.Base64EncodeStream(streams.StringStream(data))

            hoped = yield from expected.read(chunk_size)

            while hoped:
                actual = yield from stream.read(chunk_size)
                assert actual == hoped
                hoped = yield from expected.read(chunk_size)

            left_overs = yield from stream.read()

            assert left_overs == b''

    def test_size(self):
        data = b'the ode to carp'
        expected = base64.b64encode(data)
        stream = streams.Base64EncodeStream(streams.StringStream(data))

        assert len(expected) == int(stream.size)

