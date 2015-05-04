import os
import abc
import uuid
import base64
import struct
import time
import binascii
import asyncio
import zipfile
import zlib


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

    def __init__(self, response, size=None):
        super().__init__()
        self._size = size
        self.response = response
        self.content_type = self.response.headers.get('Content-Type', 'application/octet-stream')

    @property
    def size(self):
        if self._size is not None:
            return str(self._size)
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

class ProgressStreamWriter:
    def __init__(self, size):
        self._so_far = 0
        self.total = size

    def write(self, data):
        self._so_far += len(data)

    def can_write_eof(self):
        return False

    def close(self):
        pass

    @property
    def progress(self):
        return int(self._so_far / self.total * 100)


class StringStream(BaseStream):
    def __init__(self, data):
        super().__init__()
        if isinstance(data, str):
            data = data.encode('UTF-8')
        elif not isinstance(data, bytes):
            raise TypeError('Data must be either str or bytes, found {!r}'.format(type(data)))

        self._size = len(data)
        self.feed_data(data)
        self.feed_eof()

    @property
    def size(self):
        return self._size

    @asyncio.coroutine
    def _read(self, n=-1):
        return (yield from asyncio.StreamReader.read(self, n))


class MultiStream(asyncio.StreamReader):
    """Concatenate a series of `StreamReader` objects into a single stream.
    Reads from the current stream until exhausted, then continues to the next,
    etc. Used to build streaming form data for Figshare uploads.
    Originally written by @jmcarp
    """
    def __init__(self, *streams):
        self.stream = []
        self._streams = []
        self.add_streams(*streams)

    @property
    def size(self):
        return str(sum([int(x.size) for x in self._streams]) + int(self.stream.size))

    @property
    def streams(self):
        return self._streams

    def add_streams(self, *streams):
        self._streams.extend(streams)

        if not self.stream:
            self._cycle()

    @asyncio.coroutine
    def read(self, n=-1):
        if not self.stream:
            return b''

        chunk = yield from self.stream.read(n)
        if len(chunk) == n and n != -1:
            return chunk
        self._cycle()
        nextn = -1 if n == -1 else n - len(chunk)
        chunk += (yield from self.read(nextn))
        return chunk

    def _cycle(self):
        try:
            self.stream = self.streams.pop(0)
        except IndexError:
            self.stream = None


class FormDataStream(MultiStream):
    """A child of MultiSteam used to create stream friendly multipart form data requests.
    Usage:

    >>> stream = FormDataStream(key1='value1', file=FileStream(...))

    Or:

        >>> stream = FormDataStream()
        >>> stream.add_field('key1', 'value1')
        >>> stream.add_file('file', FileStream(...), mime='text/plain')

    Additional options for files can be passed as a tuple ordered as:

        >>> FormDataStream(fieldName=(FileStream(...), 'fileName', 'Mime', 'encoding'))

    Auto generates boundaries and properly concatenates them
    Use FormDataStream.headers to get the proper headers to be included with requests
    Namely Content-Length, Content-Type
    """

    @classmethod
    def make_boundary(cls):
        """Creates a random-ish boundary for
        form data seperator
        """
        return uuid.uuid4().hex

    @classmethod
    def make_header(cls, name, disposition='form-data', additional_headers=None, **extra):
        additional_headers = additional_headers or {}
        header = 'Content-Disposition: {}; name="{}"'.format(disposition, name)

        header += ''.join([
            '; {}="{}"'.format(key, value)
            for key, value
            in extra.items()
            if value is not None
        ])

        additional = '\r\n'.join([
            '{}: {}'.format(key, value)
            for key, value in additional_headers.items()
            if value is not None
        ])

        header += '\r\n'

        if additional:
            header += additional
            header += '\r\n'

        return header + '\r\n'

    def __init__(self, **fields):
        """:param dict fields: A dict of fieldname: value to create the body of the stream"""
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
    def end_boundary(self):
        return StringStream('--{}--\r\n'.format(self.boundary))

    @property
    def headers(self):
        """The headers required to make a proper multipart form request
        Implicitly calls finalize as accessing headers will often indicate sending of the request
        Meaning nothing else will be added to the stream"""
        self.finalize()

        return {
            'Content-Length': str(self.size),
            'Content-Type': 'multipart/form-data; boundary={}'.format(self.boundary)
        }

    @asyncio.coroutine
    def read(self, n=-1):
        if self.can_add_more:
            self.finalize()
        return (yield from super().read(n=n))

    def finalize(self):
        assert self.stream, 'Must add at least one stream to finalize'

        if self.can_add_more:
            self.can_add_more = False
            self.add_streams(self.end_boundary)
            # self.size = sum([int(x.size) for x in self.streams]) + self.stream.size

    def add_fields(self, **fields):
        for key, value in fields.items():
            self.add_field(key, value)

    def add_field(self, key, value):
        assert self.can_add_more, 'Cannot add more fields after calling finalize or read'

        self.add_streams(
            self._make_boundary_stream(),
            StringStream(self.make_header(key) + value + '\r\n')
        )

    def add_file(self, field_name, file_stream, file_name=None, mime='application/octet-stream', disposition='file', transcoding='binary'):
        assert self.can_add_more, 'Cannot add more fields after calling finalize or read'

        header = self.make_header(
            field_name,
            disposition=disposition,
            filename=file_name,
            additional_headers={
                'Content-Type': mime,
                'Content-Transfer-Encoding': transcoding
            }
        )

        self.add_streams(
            self._make_boundary_stream(),
            StringStream(header),
            file_stream,
            StringStream('\r\n')
        )

    def _make_boundary_stream(self):
        return StringStream('--{}\r\n'.format(self.boundary))


class Base64EncodeStream(asyncio.StreamReader):

    def __init__(self, stream, **kwargs):
        self.extra = b''
        self.stream = stream
        self.size = int(stream.size)
        self.size = (4 * self.size / 3)
        if self.size % 4:
            self.size += (4 - self.size % 4)
        self.size = str(int(self.size))
        super().__init__(**kwargs)

    @asyncio.coroutine
    def read(self, n=-1):
        if n < 0:
            return (yield from super().read(n))

        nog = n
        padding = n % 3
        if padding:
            n += (3 - padding)

        chunk = self.extra + base64.b64encode((yield from self.stream.read(n)))

        if len(chunk) <= nog:
            self.extra = b''
            return chunk

        chunk, self.extra = chunk[:nog], chunk[nog:]

        return chunk


class JSONStream(MultiStream):

    def __init__(self, data):
        streams = [StringStream('{')]
        for key, value in data.items():
            if not isinstance(value, asyncio.StreamReader):
                value = StringStream(value)
            streams.extend([StringStream('"{}":"'.format(key)), value, StringStream('",')])
        super().__init__(*(streams[:-1] + [StringStream('"}')]))
=======
class ZipStreamReader(MultiStream):

    def __init__(self, filename, file_stream):
        self.stream_index = -1
        self.original_size = 0
        self.compress_size = 0
        self.zinfo = None
        self.filename = filename
        self.header = b''
        self.data_descriptor = b''
        self.compressor = zlib.compressobj(
            zlib.Z_DEFAULT_COMPRESSION,
            zlib.DEFLATED,
            -15,
        )
        super().__init__()

        # Do not add data descriptor/footer until file_stream is read in
        self.add_streams(
            StringStream(self.make_header()),
            file_stream,
        )

    def _cycle(self):
        """Override to keep track of index, add data descriptor/footer"""
        try:
            self.stream = self.streams.pop(0)
            self.stream_index += 1
        except IndexError:
            # If we just finished the data stream, add the descriptor/footer
            if self.on_data_stream:
                self.stream = None
                self.add_streams(
                    StringStream(self.make_data_descriptor()),
                    StringStream(self.make_footer()),
                )
            else:
                self.stream = None

    def _compress(self, chunk):
        self.original_size += len(chunk)
        self.zinfo.CRC = binascii.crc32(chunk, self.zinfo.CRC)

        chunk = self.compressor.compress(chunk)
        self.compress_size += len(chunk)

        return chunk

    def _flush(self):
        chunk = self.compressor.flush()
        self.compress_size += len(chunk)
        return chunk

    @property
    def on_data_stream(self):
        return self.stream_index == 1 and self.stream is not None

    @asyncio.coroutine
    def read(self, n=-1):
        """Override to allow compression for data stream"""
        if not self.stream:
            return b''

        chunk = yield from self.stream.read(n)
        if len(chunk) == n and n != -1:
            return self._compress(chunk) if self.on_data_stream else chunk
        if self.on_data_stream:
            chunk = self._compress(chunk)
            chunk += self._flush()
        self._cycle()
        nextn = -1 if n == -1 else n - len(chunk)
        next_chunk = (yield from self.read(nextn))
        chunk += self._compress(next_chunk) if self.on_data_stream else next_chunk
        return chunk

    def make_header(self):
        self.zinfo = zipfile.ZipInfo(
            filename=self.filename,
            date_time=time.localtime(time.time())[:6],
        )
        self.zinfo.compress_type = zipfile.ZIP_DEFLATED
        self.zinfo.external_attr = 0o600 << 16
        self.zinfo.header_offset = 0
        self.zinfo.flag_bits |= 0x08
        self.zinfo.CRC = 0  # Will be updated as data is read

        self.header = self.zinfo.FileHeader(zip64=False)  # TODO: Can we support zip64?
        return self.header

    def make_data_descriptor(self):
        """Create 16 byte descriptor of file CRC, file size, and compress size"""
        fmt = '<4sLLL'
        signature = b'PK\x07\x08'  # magic number for data descriptor
        self.data_descriptor = struct.pack(
            fmt,
            signature,
            self.zinfo.CRC,
            self.compress_size,
            self.original_size,
        )
        return self.data_descriptor

    def make_footer(self):
        count = 1
        dt = self.zinfo.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        extra_data = self.zinfo.extra

        filename, flag_bits = self.zinfo._encodeFilenameFlags()
        centdir = struct.pack(
            zipfile.structCentralDir,
            zipfile.stringCentralDir,
            self.zinfo.create_version,
            self.zinfo.create_system,
            self.zinfo.extract_version,
            self.zinfo.reserved,
            flag_bits,
            self.zinfo.compress_type,
            dostime,
            dosdate,
            self.zinfo.CRC,
            self.compress_size,
            self.original_size,
            len(self.zinfo.filename),
            len(extra_data),
            len(self.zinfo.comment),
            0,
            self.zinfo.internal_attr,
            self.zinfo.external_attr,
            self.zinfo.header_offset,
        )

        footer = centdir + filename + extra_data + self.zinfo.comment

        centdir_offset = len(self.header) + self.compress_size + len(self.data_descriptor)

        endrec = struct.pack(
            zipfile.structEndArchive,
            zipfile.stringEndArchive,
            0,
            0,
            count,
            count,
            len(footer),
            centdir_offset,
            0,
        )

        footer += endrec
        return footer

    @property
    def size(self):
        header_size = struct.calcsize(zipfile.structFileHeader) + len(self.filename)
        descriptor_size = struct.calcsize('<4sLLL')
        footer_size = struct.calcsize(zipfile.structCentralDir) + len(self.filename) + struct.calcsize(zipfile.structEndArchive)

        return header_size + self.compress_size + descriptor_size + footer_size
