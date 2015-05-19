import asyncio
import binascii
import struct
import time
import zipfile
import zlib

from waterbutler.core.streams import BaseStream
from waterbutler.core.streams import MultiStream
from waterbutler.core.streams import StringStream


class ZipLocalFileDescriptor(BaseStream):
    """The descriptor (footer) for a local file in a zip archive

    Note: This class is tightly coupled to ZipStreamReader, and should not be
    used separately
    """
    def __init__(self, file):
        super().__init__()
        self.file = file

    @property
    def size(self):
        return 0

    @asyncio.coroutine
    def _read(self, *args, **kwargs):
        """Create 16 byte descriptor of file CRC, file size, and compress size"""
        self._eof = True
        return self.file.descriptor


class ZipLocalFileData(BaseStream):
    """A thin stream wrapper, used to update a ZipLocalFile as chunks are read

    Note: This class is tightly coupled to ZipStreamReader, and should not be
    used separately
    """
    def __init__(self, file, stream, *args, **kwargs):
        self.file = file
        self.stream = stream
        self._buffer = bytearray()
        super().__init__(*args, **kwargs)

    @property
    def size(self):
        return 0

    @asyncio.coroutine
    def _read(self, n=-1, *args, **kwargs):
        ret = self._buffer

        while (n == -1 or len(ret) < n) and not self.stream.at_eof():
            chunk = yield from self.stream.read(n, *args, **kwargs)

            # Update file info
            self.file.original_size += len(chunk)
            self.file.zinfo.CRC = binascii.crc32(chunk, self.file.zinfo.CRC)

            # compress
            compressed = self.file.compressor.compress(chunk)
            compressed += self.file.compressor.flush(
                zlib.Z_FINISH if self.stream.at_eof() else zlib.Z_SYNC_FLUSH
            )

            # Update file info
            self.file.compressed_size += len(compressed)
            ret += compressed

        # import ipdb; ipdb.set_trace()

        # buffer any overages
        if n != -1 and len(ret) > n:
            self._buffer = ret[n:]
            ret = ret[:n]
        else:
            self._buffer = bytearray()

        # EOF is the buffer and stream are both empty
        if not self._buffer and self.stream.at_eof():
            self.feed_eof()

        return bytes(ret)


class ZipLocalFile(MultiStream):
    """A local file in a zip archive

    Note: This class is tightly coupled to ZipStreamReader, and should not be
    used separately
    """
    def __init__(self, file_tuple):
        filename, stream = file_tuple
        filename = filename.strip('/')
        # Build a ZipInfo instance to use for the file's header and footer
        self.zinfo = zipfile.ZipInfo(
            filename=filename,
            date_time=time.localtime(time.time())[:6],
        )
        self.zinfo.compress_type = zipfile.ZIP_DEFLATED
        self.zinfo.external_attr = 0o600 << 16
        self.zinfo.header_offset = 0
        self.zinfo.flag_bits |= 0x08
        # Initial CRC: value will be updated as file is streamed
        self.zinfo.CRC = 0

        # define a compressor
        self.compressor = zlib.compressobj(
            zlib.Z_DEFAULT_COMPRESSION,
            zlib.DEFLATED,
            -15,
        )

        # meta information - needed to build the footer
        self.original_size = 0
        self.compressed_size = 0

        super().__init__(
            StringStream(self.local_header),
            ZipLocalFileData(self, stream),
            ZipLocalFileDescriptor(self),
        )

    @property
    def local_header(self):
        """The file's header, for inclusion just before the content stream"""
        return self.zinfo.FileHeader(zip64=False)

    @property
    def directory_header(self):
        """The file's header, for inclusion in the archive's central directory
        """
        dt = self.zinfo.date_time

        # modification date/time, in MSDOS format
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
            dostime,  # modification time
            dosdate,
            self.zinfo.CRC,
            self.compressed_size,
            self.original_size,
            len(self.zinfo.filename),
            len(extra_data),
            len(self.zinfo.comment),
            0,
            self.zinfo.internal_attr,
            self.zinfo.external_attr,
            self.zinfo.header_offset,
        )

        return centdir + filename + extra_data + self.zinfo.comment

    @property
    def descriptor(self):
        """Local file data descriptor"""
        fmt = '<4sLLL'
        signature = b'PK\x07\x08'  # magic number for data descriptor

        return struct.pack(
            fmt,
            signature,
            self.zinfo.CRC,
            self.compressed_size,
            self.original_size,
        )

    @property
    def total_bytes(self):
        """Length, in bytes, of output. Includes header and footer

        Note: This should be access after the file's data has been streamed.
        """
        return (
            len(self.local_header) +
            self.compressed_size +
            len(self.descriptor)
        )


class ZipArchiveCentralDirectory(BaseStream):
    """The central directory for a zip archive

    Note: This class is tightly coupled to ZipStreamReader, and should not be
    used separately
    """
    def __init__(self, files, *args, **kwargs):
        super().__init__()
        self.files = files

    @property
    def size(self):
        return 0

    @asyncio.coroutine
    def _read(self, n=-1):
        file_headers = []
        cumulative_offset = 0
        for file in self.files:
            file.zinfo.header_offset = cumulative_offset
            file_headers.append(file.directory_header)
            cumulative_offset += file.total_bytes

        file_headers = b''.join(file_headers)

        count = len(self.files)

        endrec = struct.pack(
            zipfile.structEndArchive,
            zipfile.stringEndArchive,
            0,
            0,
            count,
            count,
            len(file_headers),
            cumulative_offset,
            0,
        )
        self.feed_eof()

        return b''.join((file_headers, endrec))


class ZipStreamReader(MultiStream):
    """Combines one or more streams into a single, Zip-compressed stream"""
    def __init__(self, *streams):
        # Each incoming stream should be wrapped in a _ZipFile instance
        streams = [ZipLocalFile(each) for each in streams]

        # Append a stream for the archive's footer (central directory)
        streams.append(ZipArchiveCentralDirectory(streams.copy()))

        super().__init__(*streams)
