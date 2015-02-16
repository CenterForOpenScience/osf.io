import os
import abc
import uuid
import asyncio


class BaseStream(asyncio.StreamReader, metaclass=abc.ABCMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readers = {}
        self.writers = {}

    @abc.abstractproperty
    def size(self):
        pass

    def add_reader(self, name, reader):
        self.readers[name] = reader

    def remove_reader(self, name):
        del self.readers[name]

    def add_writer(self, name, writer):
        self.writers[name] = writer

    def remove_writer(self, name):
        del self.writers[name]

    def feed_eof(self):
        super().feed_eof()
        for reader in self.readers.values():
            reader.feed_eof()
        for writer in self.writers.values():
            if hasattr(writer, 'can_write_eof') and writer.can_write_eof():
                writer.write_eof()

    @asyncio.coroutine
    def read(self, size=-1):
        eof = self.at_eof()
        data = yield from self._read(size)
        if not eof:
            for reader in self.readers.values():
                reader.feed_data(data)
            for writer in self.writers.values():
                writer.write(data)
        return data

    @abc.abstractmethod
    @asyncio.coroutine
    def _read(self, size):
        pass


class ResponseStreamReader(BaseStream):

    def __init__(self, response):
        super().__init__()
        self.response = response
        self.content_type = self.response.headers.get('Content-Type', 'application/octet-stream')

    @property
    def size(self):
        return self.response.headers.get('Content-Length')

    @asyncio.coroutine
    def _read(self, size):
        return (yield from self.response.content.read(size))


class RequestStreamReader(BaseStream):

    def __init__(self, request):
        super().__init__()
        self.request = request

    @property
    def size(self):
        return self.request.headers.get('Content-Length')

    @asyncio.coroutine
    def _read(self, size):
        return (yield from asyncio.StreamReader.read(self, size))


class FileStreamReader(BaseStream):

    def __init__(self, file_pointer):
        super().__init__()
        self.file_gen = None
        self.file_pointer = file_pointer
        self.read_size = None
        self.content_type = 'application/octet-stream'

    @property
    def size(self):
        cursor = self.file_pointer.tell()
        self.file_pointer.seek(0, os.SEEK_END)
        ret = self.file_pointer.tell()
        self.file_pointer.seek(cursor)
        return ret

    def close(self):
        self.file_pointer.close()
        self.feed_eof()

    def read_as_gen(self):
        self.file_pointer.seek(0)
        while True:
            data = self.file_pointer.read(self.read_size)
            if not data:
                break
            yield data

    @asyncio.coroutine
    def _read(self, size):
        self.file_gen = self.file_gen or self.read_as_gen()
        # add sleep of 0 so read will yield and continue in next io loop iteration
        yield from asyncio.sleep(0)
        self.read_size = size
        try:
            return next(self.file_gen)
        except StopIteration:
            return b''


class HashStreamWriter:
    """Stream-like object that hashes and discards its input."""
    def __init__(self, hasher):
        self.hash = hasher()

    @property
    def hexdigest(self):
        return self.hash.hexdigest()

    def can_write_eof(self):
        return False

    def write(self, data):
        self.hash.update(data)

    def close(self):
        pass


class MultiStream(asyncio.StreamReader):
    """Concatenate a series of `StreamReader` objects into a single stream.
    Reads from the current stream until exhausted, then continues to the next,
    etc. Used to build streaming form data for Figshare uploads.
    """
    def __init__(self, *streams):
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


class FormDataStream(MultiStream):
    """Concatenate a series of `StreamReader` objects into a single stream.
    Reads from the current stream until exhausted, then continues to the next,
    etc. Used to build streaming form data for Figshare uploads.
    """
    FORM_DATA_HEADER = 'Content-Disposition: form-data; name="{}"\r\n\r\n'
    FILE_HEADER = 'Content-Disposition: file; {}filename="{}"\r\nContent-Type: {}\r\nContent-Transfer-Encoding: {}\r\n\r\n'

    @classmethod
    def make_boundary(self):
        return uuid.uuid4().hex

    def __init__(self, **fields):
        self.can_add_more = True
        self.boundary = self.make_boundary()
        super().__init__()

        for key, value in fields.items():
            if isinstance(value, tuple):
                self.add_file(key, *value)
            elif isinstance(value, asyncio.StreamReader):
                self.add_file(key, value)
            else:
                self.add_field(key, value)

    @property
    def headers(self):
        assert not self.can_add_more, 'Must call finalize or read before getting headers.'

        return {
            'Content-Length': self.size,
            'Content-Type': 'multipart/form-data, boundry={}'.format(self.boundry)
        }

    @asyncio.coroutine
    def read(self, n=-1):
        if self.can_add_more:
            self.finalize()
        return super().read(n=n)

    def finalize(self):
        if self.can_add_more:
            if not self.stream and self.streams:
                self.cycle()
            self.can_add_more = False
            self.streams.append(self.end_boundary)
            self.size = sum([x.size for x in self.streams])

    def add_file(self, file_name, file_stream, field_name=None, mime='application/octet-stream', transcoding='binary'):
        assert self.can_add_more, 'Cannot add more fields after calling finalize or read'

        if field_name:
            field_name = 'name="{}"; '.format(field_name)
        else:
            field_name = ''

        self.streams.extend([
            self._make_boundary_stream(),
            StringStream(
                self.FILE_HEADER.format(
                    field_name,
                    file_name,
                    mime,
                    transcoding
                )
            ),
            file_stream
        ])

    def add_field(self, key, value):
        assert self.can_add_more, 'Cannot add more fields after calling finalize or read'

        self.streams.extend([
            self._make_boundary_stream(),
            StringStream(self.FORM_DATA_HEADER.format(key) + value + '\r\n')
        ])

    def _make_boundary_stream(self):
        return StringStream('--{}\r\n'.format(self.boundary))

    @property
    def end_boundary(self):
        return StringStream('--{}--\r\n'.format(self.boundary))


class StringStream(asyncio.StreamReader):
    def __init__(self, data):
        super().__init__()
        if isinstance(data, str):
            data = data.encode('UTF-8')
        elif not isinstance(data, bytes):
            raise TypeError('Data must be either str or bytes, found {!r}'.format(type(data)))

        self.feed_data(data)
        self.size = len(data)

        self.feed_eof()


def make_headers(**options):
    fields = '; '.join('{0}="{1}"'.format(key, value) for key, value in options.items())
    return 'Content-Disposition: form-data; {0}\r\n\r\n'.format(fields).encode('utf-8')


def make_upload_data(stream, **options):
    """Prepare upload form data stream for Figshare. Wraps input stream in form
    data boundary streams.

    :returns: Tuple of (<stream>, <boundary>, <size>)
    """
    boundary = make_boundary()
    boundaries = make_boundary_streams(boundary, **options)
    outstream = MultiStream(
        boundaries[0][0],
        stream,
        boundaries[1][0],
    )
    size = boundaries[0][1] + int(stream.size) + boundaries[1][1]
    return outstream, boundary, size
