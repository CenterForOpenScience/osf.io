# encoding: utf-8

import os
import abc
from asyncio import coroutine
from asyncio import StreamReader

import furl

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


class ResponseWrapper(object):

    def __init__(self, response):
        self.response = response
        self.content = response.content
        self.size = response.headers.get('Content-Length')
        self.content_type = response.headers.get('Content-Type', 'application/octet-stream')


class RequestWrapper(object):

    def __init__(self, request):
        self.response = request
        self.content = StreamReader()
        self.size = request.headers.get('Content-Length')


class FileWrapper(object):

    def __init__(self, file_pointer):
        self.file_pointer = file_pointer
        self.content = StreamReader()
        # TODO: Handle UTF-unsafe characters
        self.content.feed_data(file_pointer.read())
        self.content.feed_eof()
        self.size = file_pointer.tell()


class BaseProvider(metaclass=abc.ABCMeta):

    BASE_URL = None

    def __init__(self, auth, identity):
        self.auth = auth
        self.identity = identity

    def build_url(self, *segments, base_url=None, **query):
        url = furl.furl(base_url or self.BASE_URL)
        url.path = os.path.join(*segments)
        url.args = query
        return url.url

    def can_intra_copy(self, other):
        return False

    def can_intra_move(self, other):
        return False

    def intra_copy(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    def intra_move(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    @coroutine
    def copy(self, dest_provider, source_options, dest_options):
        if self.can_intra_copy(dest_provider):
            try:
                return (yield from self.intra_copy(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        obj = yield from self.download(**source_options)
        yield from dest_provider.upload(obj, **dest_options)

    @coroutine
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
    def upload(self, obj, **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, **kwargs):
        pass

    @abc.abstractmethod
    def metadata(self, **kwargs):
        pass
