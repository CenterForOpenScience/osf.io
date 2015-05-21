import json
import pytest
from tests.utils import async
from waterbutler.core import streams

class TestJSONStream:

    @async
    def test_single_element_strings(self):
        data = {
            'key': 'value'
        }

        stream = streams.JSONStream(data)

        read = yield from stream.read()

        assert data == json.loads(read.decode('utf-8'))

    @async
    def test_multielement(self):
        data = {
            'key': 'value',
            'json': 'has',
            'never': 'looked',
            'this': 'cool'
        }

        stream = streams.JSONStream(data)

        read = yield from stream.read()

        assert data == json.loads(read.decode('utf-8'))

    def test_other_streams(self):
        stream = streams.JSONStream({
            'justAStream': streams.StringStream('These are some words')
        })

        read = yield from stream.read()

        assert json.loads(read.decode('utf-8')) == {
            'justAStream': 'These are some words'
        }

    def test_other_streams_1_at_a_time(self):
        stream = streams.JSONStream({
            'justAStream': streams.StringStream('These are some words')
        })

        buffer = b''
        chunk = yield from stream.read(1)

        while chunk:
            buffer += chunk
            chunk = yield from stream.read(1)

        assert json.loads(buffer.decode('utf-8')) == {
            'justAStream': 'These are some words'
        }

    def test_github(self):
        stream = streams.JSONStream({
            'encoding': 'base64',
            'content': streams.Base64EncodeStream(streams.StringStream('These are some words')),
        })

        buffer = b''
        chunk = yield from stream.read(1)

        while chunk:
            buffer += chunk
            chunk = yield from stream.read(1)

        assert json.loads(buffer.decode('utf-8')) == {
            'encoding': 'base64',
            'content': 'VGhlc2UgYXJlIHNvbWUgd29yZHM='
        }

    def test_github_at_once(self):
        stream = streams.JSONStream({
            'encoding': 'base64',
            'content': streams.Base64EncodeStream(streams.StringStream('These are some words')),
        })

        buffer = yield from stream.read()

        assert json.loads(buffer.decode('utf-8')) == {
            'encoding': 'base64',
            'content': 'VGhlc2UgYXJlIHNvbWUgd29yZHM='
        }


    # TODO
    # @async
    # def test_nested_streams(self):
    #     data = {
    #         'key': 'value',
    #         'json': 'has',
    #         'never': 'looked',
    #         'this': 'cool',
    #     }

    #     stream = streams.JSONStream({
    #         'outer': streams.JSONStream({'inner': streams.JSONStream(data)}),
    #         'justAStream': streams.StringStream('These are some words')
    #     })

    #     read = yield from stream.read()

    #     assert json.loads(read.decode('utf-8')) == {
    #         'outer': {
    #             'inner': data
    #         },
    #         'justAStream': 'These are some words'
    #     }

