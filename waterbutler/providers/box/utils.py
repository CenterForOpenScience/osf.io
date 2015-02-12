import http
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
        raise exceptions.MetadataError(
            'Could not resolve file with ID {0}'.format(file_id),
            code=http.client.NOT_FOUND,
        )


class MultiStream(asyncio.StreamReader):
    """Concatenate a series of `StreamReader` objects into a single stream.
    Reads from the current stream until exhausted, then continues to the next,
    etc. Used to build streaming form data for Figshare uploads.
    """
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


def make_headers(stream, **options):
    #fields = '; '.join('{0}="{1}"'.format(key, value) for key, value in options.items())
    fields = []
    for key, value in options.items():
        if key=='file':
            fields.append('Content-Disposition: form-data; name="{1}"; filename="{1}"\r\n\r\n'.format(key, value, stream).encode('utf-8'))
        else:
            fields.insert(0, 'Content-Disposition: form-data; name="{0}"\r\n\r\n{1}\r\n'.format(key, value).encode('utf-8'))

    return fields #'Content-Disposition: form-data; {0}\r\n\r\n'.format(fields).encode('utf-8')


def make_boundary_streams(boundary, stream, **options):
    headers = make_headers(stream, **options)
    return (
        wrap_stream(b'--' + boundary + b'\r\n' + headers[0]),
        wrap_stream(b'--' + boundary + b'\r\n' + headers[1]),
        wrap_stream(b'\r\n--' + boundary + b'--\r\n'),
    )


def make_upload_data(stream, **options):
    """Prepare upload form data stream for Figshare. Wraps input stream in form
    data boundary streams.

    :returns: Tuple of (<stream>, <boundary>, <size>)
    """
    boundary = make_boundary()
    boundaries = make_boundary_streams(boundary, stream, **options)
    outstream = MultiStream(
        boundaries[0][0],
        #stream,
        boundaries[1][0],
        boundaries[2][0]
    )
    size = boundaries[0][1] + boundaries[1][1] + boundaries[2][1] #+ int(stream.size) 
    return outstream, boundary, size
