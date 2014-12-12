import os
import abc
import asyncio
import functools
import itertools

import furl
import aiohttp

from waterbutler.exceptions import exception_from_reponse


PROVIDERS = {}


def register_provider(name):
    def _register_provider(cls):
        if PROVIDERS.get(name):
            raise ValueError('{} is already a registered provider'.format(name))
        PROVIDERS[name] = cls
        return cls
    return _register_provider


def get_provider(name):
    try:
        return PROVIDERS[name]
    except KeyError:
        raise NotImplementedError('No provider for {}'.format(name))


def make_provider(name, credentials):
    return get_provider(name)(credentials['auth'], credentials['identity'])


def expects(*codes):
    def wrapper(func):
        assert asyncio.iscoroutinefunction(func)
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            result = yield from func(*args, **kwargs)
            if result.response.status not in codes:
                raise (yield from exception_from_reponse(result.response, **kwargs))
            return result
        return wrapped
    return wrapper


class BaseStream(asyncio.StreamReader, metaclass=abc.ABCMeta):

    def __init__(self):
        self.hashes = {}
        self.size = None

    def set_hashes(self, *hashes):
        self.hashes = {}
        for hash in hashes:
            hasher = hash()
            self.hashes[hasher.name] = hasher

    def feed_hashes(self, chunk):
        for hash in self.hashes.values():
            hash.update(chunk)

    @asyncio.coroutine
    def read(self, size=None):
        chunk = yield from self._read(size)
        self.feed_hashes(chunk)
        return chunk

    @abc.abstractmethod
    @asyncio.coroutine
    def _read(self, chunk):
        pass


class ResponseStream(BaseStream):

    def __init__(self, response):
        super().__init__()
        self.response = response
        self.size = response.headers.get('Content-Length')
        self.content_type = response.headers.get('Content-Type', 'application/octet-stream')

    @asyncio.coroutine
    def _read(self, size=None):
        return (yield from self.response.content.read(size))


class RequestStream(BaseStream):

    def __init__(self, request):
        super().__init__()
        self.request = request
        self.size = self.request.headers.get('Content-Length')

    @asyncio.coroutine
    def _read(self, size=None):
        return (yield from self.request.content.read(size))


class FileStream(BaseStream):

    def __init__(self, file_object):
        super().__init__()
        self.file_gen = self.read_as_gen()
        self.file_object = file_object
        self.file_object.seek(os.SEEK_END)
        self.read_size = None
        self.size = self.file_object.tell()

    @asyncio.coroutine
    def _read(self, size=None):
        # add sleep of 0 so read will yield and continue in next io loop iteration
        yield from asyncio.sleep(0)
        self.read_size = size
        try:
            return next(self.file_gen)
        except StopIteration:
            return b''

    def read_as_gen(self):
        self.file_object.seek(0)

        while True:
            data = self.file_object.read(self.read_size)
            if not data:
                break
            yield data


def build_url(base, *segments, **query):
    url = furl.furl(base)
    segments = filter(
        lambda segment: segment,
        map(
            lambda segment: segment.strip('/'),
            itertools.chain(url.path.segments, segments)
        )
    )
    url.path = os.path.join(*segments)
    url.args = query
    return url.url


class BaseProvider(metaclass=abc.ABCMeta):

    BASE_URL = None

    def __init__(self, auth, identity):
        self.auth = auth
        self.identity = identity

    def build_url(self, *segments, **query):
        return build_url(self.BASE_URL, *segments, **query)

    @property
    def default_headers(self):
        return {}

    def build_headers(self, **kwargs):
        headers = self.default_headers
        headers.update(kwargs)
        return {
            key: value
            for key, value in headers.items()
            if value is not None
        }

    @asyncio.coroutine
    def make_request(self, *args, **kwargs):
        kwargs['headers'] = self.build_headers(**kwargs.get('headers', {}))
        response = yield from aiohttp.request(*args, **kwargs)
        return response

    def can_intra_copy(self, other):
        return False

    def can_intra_move(self, other):
        return False

    def intra_copy(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    def intra_move(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    @asyncio.coroutine
    def copy(self, dest_provider, source_options, dest_options):
        if self.can_intra_copy(dest_provider):
            try:
                return (yield from self.intra_copy(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        stream = yield from self.download(**source_options)
        yield from dest_provider.upload(stream, **dest_options)

    @asyncio.coroutine
    def move(self, dest_provider, source_options, dest_options):
        if self.can_intra_move(dest_provider):
            try:
                return (yield from self.intra_move(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        yield from self.copy(dest_provider, source_options, dest_options)
        yield from self.delete(**source_options)

    @abc.abstractmethod
    def download(self, **kwargs):
        pass

    @abc.abstractmethod
    def upload(self, stream, **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, **kwargs):
        pass

    @abc.abstractmethod
    def metadata(self, **kwargs):
        pass
