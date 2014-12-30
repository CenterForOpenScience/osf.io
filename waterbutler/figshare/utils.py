import uuid
import asyncio

from waterbutler.core import exceptions


def file_or_error(article, file_id):
    try:
        return next(
            each for each in article['files']
            if each['id'] == int(file_id)
        )
    except StopIteration:
        raise exceptions.MetadataError


class MultiStream(asyncio.StreamReader):

    def __init__(self, *streams):
        self._streams = streams
        self.streams = list(streams)
        self.cycle()

    def cycle(self):
        try:
            self.stream = self.streams.pop(0)
        except IndexError:
            self.stream = None

    @asyncio.coroutine
    def read(self, n=-1):
        if not self.stream:
            return b''
        chunk = yield from self.stream.read(n)
        if len(chunk) == n and n != -1:
            return chunk
        self.cycle()
        nextn = -1 if n == -1 else n - len(chunk)
        chunk += (yield from self.read(nextn))
        return chunk


def wrap_stream(data):
    stream = asyncio.StreamReader()
    stream.feed_data(data)
    stream.feed_eof()
    return stream, len(data)


def make_boundary():
    return uuid.uuid4().hex.encode('utf-8')


def make_headers(**options):
    fields = '; '.join('{0}="{1}"'.format(key, value) for key, value in options.items())
    return 'Content-Disposition: form-data; {0}\r\n\r\n'.format(fields).encode('utf-8')


def make_boundary_streams(boundary, **options):
    headers = make_headers(**options)
    return (
        wrap_stream(b'--' + boundary + b'\r\n' + headers),
        wrap_stream(b'\r\n--' + boundary + b'--\r\n'),
    )


def make_upload_data(stream, **options):
    boundary = make_boundary()
    boundaries = make_boundary_streams(boundary, **options)
    outstream = MultiStream(
        boundaries[0][0],
        stream,
        boundaries[1][0],
    )
    size = boundaries[0][1] + stream.size + boundaries[1][1]
    return outstream, boundary, size
