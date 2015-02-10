import os
import abc
import asyncio

from io import BytesIO
from zipfile import ZipFile

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


class ZipStreamReader(RequestStreamReader):
        
    def __init__(self, request_stream):
        super().__init__(request_stream.request)
        self._cursor = 0

    @asyncio.coroutine
    def read(self, size=-1):
        eof = self.at_eof()
        data = yield from self._read(size)
        zf = ZipFile(self._buffer, mode='ab', compression=0)
        zf.writestr(a)        
        data = zf.read()
        if not eof:
            for reader in self.readers.values():
                reader.feed_data(data)
            for writer in self.writers.values():
                writer.write(data)
        return data


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
