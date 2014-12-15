import os
import abc
import asyncio
import logging
import functools
import itertools

import furl
import aiohttp

from waterbutler.exceptions import exception_from_reponse

logger = logging.getLogger(__name__)

PROVIDERS = {}


def register_provider(name):
    """A decorator that adds the specifed class into the `PROVIDERS` dict
    :param str name: The name to register
    """
    def _register_provider(cls):
        if PROVIDERS.get(name):
            logging.warning('{} is already a registered provider'.format(name))

        PROVIDERS[name] = cls
        return cls
    return _register_provider


def get_provider(name):
    """Return the provider *class* of the registed name
    Raises a NotImplementedError if one is not found
    :param str name: Name of the provider to find
    :rtype type(BaseProvider):
    """
    try:
        return PROVIDERS[name]
    except KeyError:
        raise NotImplementedError('No provider for {}'.format(name))


def make_provider(name, credentials):
    """Fetches a provider registed under name and returns an instance of it
    :param str name: Name of the provider
    :param dict credentials: a dictionary containing keys `auth` and `identity`
    :rtype BaseProvider:
    """
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
