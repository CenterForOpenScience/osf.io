import asyncio

from waterbutler.core.streams import StringStream
from waterbutler.core.streams import MultiStream


class JSONStream(MultiStream):

    def __init__(self, data):
        streams = [StringStream('{')]
        for key, value in data.items():
            if not isinstance(value, asyncio.StreamReader):
                value = StringStream(value)
            streams.extend([StringStream('"{}":"'.format(key)), value, StringStream('",')])
        super().__init__(*(streams[:-1] + [StringStream('"}')]))
