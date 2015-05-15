import base64
import asyncio


class Base64EncodeStream(asyncio.StreamReader):

    @staticmethod
    def calculate_encoded_size(size):
        size = 4 * size / 3
        if size % 4:
            size += 4 - size % 4
        return int(size)

    def __init__(self, stream, **kwargs):
        self.extra = b''
        self.stream = stream
        if stream.size is None:
            self._size = None
        else:
            self._size = Base64EncodeStream.calculate_encoded_size(stream.size)

        super().__init__(**kwargs)

    @property
    def size(self):
        return self._size

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
