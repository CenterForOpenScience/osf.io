# encoding: utf-8

import abc

from asyncio import coroutine
from asyncio import StreamReader


class ResponseWrapper(object):

    def __init__(self, response):
        self.response = response
        self.content = response.content
        self.size = response.headers.get('Content-Length')


class RequestWrapper(object):

    def __init__(self, request):

        self.response = request
        self.content = StreamReader()
        self.size = request.headers.get('Content-Length')


class BaseProvider(metaclass=abc.ABCMeta):

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


class StorageProvider(object):

    @staticmethod
    def get(info):
        name = info['name']
        if name == 'dropbox':
            from providers.contrib.dropbox import DropboxProvider
            return DropboxProvider(**info)
        elif name == 's3':
            from providers.contrib.s3 import S3Provider
            return S3Provider(**info)
        else:
            raise NotImplementedError
