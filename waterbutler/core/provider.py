import os
import abc
import asyncio
import logging
import itertools

import furl
import aiohttp

from waterbutler.core import exceptions


logger = logging.getLogger(__name__)


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

    def __init__(self, auth, credentials, settings):
        self.auth = auth
        self.credentials = credentials
        self.settings = settings

    def __eq__(self, other):
        try:
            return (
                type(self) == type(other) and
                self.identity == other.identity
            )
        except AttributeError:
            return False

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

    def build_path(self, path, prefix_slash=True, suffix_slash=True):
        """Validates and converts a WaterButler specific path to a Provider specific path.
        :param str path: WaterButler specific path
        :rtype str: Provider specific path
        """
        self.validate_path(path)

        if not prefix_slash:
            path = path.lstrip('/')
        if not suffix_slash:
            path = path.rstrip('/')

        return path

    def validate_path(self, path):
        """Validates a WaterButler specific path, e.g. /folder/file.txt
        :param str path: WaterButler path
        """
        if not path:
            raise ValueError('Must specify path')
        if not path.startswith('/'):
            raise ValueError('Invalid path \'{}\' specified'.format(path))
        # Do not allow path manipulation via shortcuts, e.g. '..'
        absolute_path = os.path.abspath(path)
        if path.endswith('/'):
            absolute_path += '/'
        if not path == absolute_path:
            raise ValueError('Invalid path \'{}\' specified'.format(absolute_path))

    @asyncio.coroutine
    def make_request(self, *args, **kwargs):
        kwargs['headers'] = self.build_headers(**kwargs.get('headers', {}))
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', exceptions.ProviderError)
        response = yield from aiohttp.request(*args, **kwargs)
        if expects and response.status not in expects:
            raise (yield from exceptions.exception_from_response(response, error=throws, **kwargs))
        return response

    def can_intra_copy(self, other):
        return False

    def can_intra_move(self, other):
        return False

    def intra_copy(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        resp = yield from self.intra_copy(dest_provider, source_options, dest_options)
        yield from self.delete(**source_options)
        return resp

    @asyncio.coroutine
    def copy(self, dest_provider, source_options, dest_options):
        if self.can_intra_copy(dest_provider):
            try:
                return (yield from self.intra_copy(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        stream = yield from self.download(**source_options)
        return (yield from dest_provider.upload(stream, **dest_options))

    @asyncio.coroutine
    def move(self, dest_provider, source_options, dest_options):
        if self.can_intra_move(dest_provider):
            try:
                return (yield from self.intra_move(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        metadata = yield from self.copy(dest_provider, source_options, dest_options)
        yield from self.delete(**source_options)
        return metadata

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

    def revisions(self, **kwargs):
        return []
