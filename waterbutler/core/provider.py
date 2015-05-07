import os
import abc
import asyncio
import itertools

import furl
import aiohttp

from waterbutler.core import exceptions
from waterbutler.core import utils
from waterbutler.core import streams


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
    """The base class for all providers.
    Every provider must, at the least,
    implement all abstract methods in this class

    .. note::
        When adding a new provider you must add it to setup.py's
        `entry_points` under the `waterbutler.providers` key formatted
        as: `<provider name> = waterbutler.providers.yourprovider:<FullProviderName>`

        Keep in mind that `yourprovider` modules must export the provider class
    """

    BASE_URL = None

    def __init__(self, auth, credentials, settings):
        """
        :param dict auth: Information about the user this provider will act on the behalf of
        :param dict credentials: The credentials used to authenticate with the provider,
            ofter an OAuth 2 token
        :param dict settings: Configuration settings for this provider,
            often folder or repo
        """
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
        """A nice wrapped around furl, builds urls based on self.BASE_URL

        :param (str, ...) segments: A tuple of string joined into /foo/bar/..
        :param dict query: A dictionary that will be turned into query parameters ?foo=bar
        :rtype: str
        """
        return build_url(self.BASE_URL, *segments, **query)

    @property
    def default_headers(self):
        """Headers to be included with every request
        Commonly OAuth headers or Content-Type
        """
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
        """A wrapper around :func:`aiohttp.request`. Inserts default headers.

        :param str method: The HTTP method
        :param str url: The url to send the request to
        :keyword expects: An optional tuple of HTTP status codes as integers raises an exception
            if the returned status code is not in it.
        :type expects: tuple of ints
        :param Exception throws: The exception to be raised from expects
        :param tuple \*args: args passed to :func:`aiohttp.request`
        :param dict \*kwargs: kwargs passed to :func:`aiohttp.request`
        :rtype: :class:`aiohttp.Response`
        :raises ProviderError: Raised if expects is defined
        """
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
        """Moves a file or folder from the current provider to the specified one
        Performs a copy and then a delete.
        Calls :func:`BaseProvider.intra_move` if possible.

        :param BaseProvider dest_provider: The provider to move to
        :param dict source_options: A dict to be sent to either :func:`BaseProvider.intra_move`
            or :func:`BaseProvider.copy` and :func:`BaseProvider.delete`
        :param dict dest_options: A dict to be sent to either :func:`BaseProvider.intra_move`
            or :func:`BaseProvider.copy`
        """
        if self.can_intra_move(dest_provider):
            try:
                return (yield from self.intra_move(dest_provider, source_options, dest_options))
            except NotImplementedError:
                pass
        metadata = yield from self.copy(dest_provider, source_options, dest_options)
        yield from self.delete(**source_options)
        return metadata

    @asyncio.coroutine
    def zip(self, path, **kwargs):
        """Streams a Zip archive of the given folder

        :param str path: The folder to compress
        """
        base_path = utils.WaterButlerPath(path)
        if not base_path.is_dir:
            raise exceptions.NotFoundError()

        files = []
        remaining = [(base_path, ())]  # (WaterButlerPath, ('path', 'to'))
        while remaining:
            name, relative_path = remaining.pop()
            kwargs['path'] = str(name)
            metadata = yield from self.metadata(**kwargs)

            for item in metadata:
                path = utils.WaterButlerPath(item['path'])
                name = item.get('name', str(path))
                if path.is_file:
                    kw = kwargs.copy()
                    kw['path'] = str(path)
                    files.append((
                        '/'.join(relative_path + (name, )),  # path
                        (yield from self.download(**kw))  # download stream
                    ))
                elif path.is_dir:
                    remaining.append((path, relative_path + (name, )))

        return streams.ZipStreamReader(*files)

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

    def create_folder(self, *args, **kwargs):
        """Create a folder in the current provider
        returns True if the folder was created; False if it already existed

        :rtype FolderMetadata:
        :raises: waterbutler.ProviderError
        """
        raise exceptions.ProviderError({'message': 'Folder creation not supported.'}, code=405)
