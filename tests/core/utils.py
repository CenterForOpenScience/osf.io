import asyncio

from waterbutler.core import provider
from waterbutler.core.path import WaterButlerPath


class MockProvider1(provider.BaseProvider):

    NAME = 'MockProvider1'

    @asyncio.coroutine
    def validate_path(self, path):
        return WaterButlerPath(path)

    @asyncio.coroutine
    def upload(self, path):
        return {}, True

    @asyncio.coroutine
    def delete(self, path):
        pass

    @asyncio.coroutine
    def metadata(self, path, throw=None):
        if throw:
            raise throw
        return {}

    @asyncio.coroutine
    def download(self, path):
        return b''

class MockProvider2(provider.BaseProvider):

    NAME = 'MockProvider2'

    def can_intra_move(self, other, path=None):
        return self.__class__ == other.__class__

    def can_intra_copy(self, other, path=None):
        return self.__class__ == other.__class__

    @asyncio.coroutine
    def validate_path(self, path):
        return WaterButlerPath(path)

    @asyncio.coroutine
    def upload(self, path):
        return {}, True

    @asyncio.coroutine
    def delete(self, path):
        pass

    @asyncio.coroutine
    def metadata(self, path):
        return {}

    @asyncio.coroutine
    def download(self, path):
        return b''
