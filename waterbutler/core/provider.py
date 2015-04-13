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

        if source_options['path'].endswith('/'):
            return (yield from self._copy_folder(dest_provider, source_options, dest_options))

        if dest_options['path'].endswith('/'):
            dest_options['path'] += os.path.split(source_options['path'])[1]

        return (yield from self._copy_file(dest_provider, source_options, dest_options))

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
    def _copy_file(self, dest_provider, source_options, dest_options):
        return (yield from dest_provider.upload(
            (yield from self.download(**source_options)),
            **dest_options
        ))

    @asyncio.coroutine
    def _copy_folder(self, dest_provider, source_options, dest_options):
        try:
            folder = yield from dest_provider.create_folder(**dest_options)
        except exceptions.CreateFolderError as e:
            if e.code != 409:
                raise
            #TODO
        for file in (yield from self.metadata(**source_options)):
            yield from self._copy_file(dest_provider, {
                'path': file['path']
            }, dict(dest_options, **{
                'path': os.path.join(dest)
            }))
        return folder

    @asyncio.coroutine
    def exists(self, path, **kwargs):
        try:
            return (yield from self.metadata(path, **kwargs))
        except exceptions.MetadataError as e:
            if e.code != 404:
                raise
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

    def create_folder(self, *args, **kwargs):
        """Create a folder in the current provider
        returns True if the folder was created; False if it already existed

        :rtype FolderMetadata:
        :raises: waterbutler.ProviderError
        """
        raise exceptions.ProviderError({'message': 'Folder creation not supported.'}, code=405)
