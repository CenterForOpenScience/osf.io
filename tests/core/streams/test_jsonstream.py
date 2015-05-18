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

