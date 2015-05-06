import asyncio
import binascii
import struct
import time
import zipfile
import zlib

from waterbutler.core.streams import MultiStream
from waterbutler.core.streams import StringStream


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
