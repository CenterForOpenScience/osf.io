import os
import abc
import asyncio
import itertools

import furl
import aiohttp

from waterbutler.core import exceptions


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

    @abc.abstractproperty
    def NAME(self):
        raise NotImplementedError

    def __eq__(self, other):
        try:
            return (
                type(self) == type(other) and
                self.credentials == other.credentials
            )
        except AttributeError:
            return False

    def serialized(self):
        return {
            'name': self.NAME,
            'auth': self.auth,
            'settings': self.settings,
            'credentials': self.credentials,
        }

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
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', exceptions.ProviderError)
        response = yield from aiohttp.request(*args, **kwargs)
        if expects and response.status not in expects:
            raise (yield from exceptions.exception_from_response(response, error=throws, **kwargs))
        return response

    def can_intra_copy(self, other):
        """Indicates if a quick copy can be performed
        between the current and `other`.

        .. note::
            Defaults to False

        :param waterbutler.core.provider.BaseProvider other: The provider to check against
        :rtype: bool
        """
        return False

    def can_intra_move(self, other):
        """Indicates if a quick move can be performed
        between the current and `other`.

        .. note::
            Defaults to False

        :param waterbutler.core.provider.BaseProvider other: The provider to check against
        :rtype: bool
        """
        return False

    def intra_copy(self, dest_provider, source_options, dest_options):
        raise NotImplementedError

    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        data, created = yield from self.intra_copy(dest_provider, source_options, dest_options)
        yield from self.delete(**source_options)
        return data, created

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

    @asyncio.coroutine
    def exists(self, path, **kwargs):
        try:
            return (yield from self.metadata(path, **kwargs))
        except exceptions.MetadataError:
            return False

    @asyncio.coroutine
    def handle_name_conflict(self, path, conflict='replace', **kwargs):
        """Given a name and a conflict resolution pattern determine
        the correct file path to upload to and indicate if that file exists or not

        :param WaterbutlerPath path: An object supporting the waterbutler path API
        :param str conflict: replace or keep
        :rtype: (WaterButlerPath, dict or None)
        """
        exists = yield from self.exists(str(path), **kwargs)
        if not exists or conflict != 'keep':
            return path, exists

        while (yield from self.exists(str(path.increment_name()), **kwargs)):
            pass
        # path.increment_name()
        # exists = self.exists(str(path))
        return path, False

    @abc.abstractmethod
    def download(self, **kwargs):
        pass

    @abc.abstractmethod
    def upload(self, stream, conflict='replace', **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, **kwargs):
        pass

    @abc.abstractmethod
    def metadata(self, **kwargs):
        pass

    def revisions(self, **kwargs):
        return []
