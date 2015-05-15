import pytest
import functools
from unittest import mock

from tests.utils import async

from waterbutler.core import streams


@pytest.fixture(autouse=True)
def boundary(monkeypatch):
    boundary = 'thisisaknownvalue'
    monkeypatch.setattr(streams.FormDataStream, 'make_boundary', lambda _: boundary)
    return boundary


class TestFormDataStream:

    def test_cant_add_after_finalize(self):
        stream = streams.FormDataStream(valjean='24601')
        stream.finalize()

        with pytest.raises(AssertionError):
            stream.add_field('javer', 'thelaw')

    def test_headers_calls_finalize(self):
        stream = streams.FormDataStream(valjean='24601')
        orig = stream.finalize
        stream.finalize = mock.Mock(side_effect=orig)

        stream.headers

        assert stream.finalize.called

    @async
    def test_add_field(self):
        stream = streams.FormDataStream()
        stream.add_field('Master of the house', 'Isnt worth my spit')

        data = yield from stream.read()

        expected = '\r\n'.join([
            '--thisisaknownvalue',
            'Content-Disposition: form-data; name="Master of the house"',
            '',
            'Isnt worth my spit',
            '--thisisaknownvalue--',
            ''
        ]).encode('utf-8')

        assert data == expected

    @async
    def test_add_fields(self):
        stream = streams.FormDataStream()
        stream.add_fields(**{
            'Master of the house': 'Isnt worth my spit',
            'Comforter, Philosopher': 'A life long prick'
        })

        data = yield from stream.read()

        expected = '\r\n'.join(sorted([
            '--thisisaknownvalue',
            'Content-Disposition: form-data; name="Comforter, Philosopher"',
            '',
            'A life long prick',
            '--thisisaknownvalue',
            'Content-Disposition: form-data; name="Master of the house"',
            '',
            'Isnt worth my spit',
            '--thisisaknownvalue--',
            ''
        ]))

        to_compare = '\r\n'.join(sorted(data.decode('utf-8').split('\r\n')))

        assert expected == to_compare

    @async
    def test_content_length(self):
        stream = streams.FormDataStream()
        stream.add_field('Master of the house', 'Isnt worth my spit')

        expected_length = int(stream.headers['Content-Length'])

        data = yield from stream.read()

        assert len(data) == stream.size
        assert len(data) == expected_length

    @async
    def test_file(self):
        stream = streams.FormDataStream(file=streams.StringStream('Empty chairs at empty tables'))

        data = yield from stream.read()

        expected = sorted([
            '--thisisaknownvalue',
            'Content-Disposition: file; name="file"',
            'Content-Type: application/octet-stream',
            'Content-Transfer-Encoding: binary',
            '',
            'Empty chairs at empty tables',
            '--thisisaknownvalue--',
            ''
        ])

        actual = sorted(data.decode('utf-8').split('\r\n'))

        assert expected == actual

    def test_finalize_empty(self):
        stream = streams.FormDataStream()

        with pytest.raises(AssertionError):
            stream.finalize()

    @async
    def test_add_field_is_ordered(self):
        stream = streams.FormDataStream()
        stream.boundary = 'thisisaknownvalue'
        stream.add_field('Master of the house', 'Isnt worth my spit')
        stream.add_field('Comforter, Philosopher', 'A life long prick')

        data = yield from stream.read()

        expected = '\r\n'.join([
            '--thisisaknownvalue',
            'Content-Disposition: form-data; name="Master of the house"',
            '',
            'Isnt worth my spit',
            '--thisisaknownvalue',
            'Content-Disposition: form-data; name="Comforter, Philosopher"',
            '',
            'A life long prick',
            '--thisisaknownvalue--',
            ''
        ]).encode('utf-8')

        assert expected == data
