import abc
import asyncio
import itertools
from urllib import parse

import furl
import aiohttp

from waterbutler.core import streams
from waterbutler.core import exceptions


def build_url(base, *segments, **query):
    url = furl.furl(base)
    # Filters return generators
    # Cast to list to force "spin" it
    url.path.segments = list(filter(
        lambda segment: segment,
        map(
            # Furl requires everything to be quoted or not, no mixtures allowed
            # prequote everything so %signs don't break everything
            lambda segment: parse.quote(segment.strip('/')),
            # Include any segments of the original url, effectively list+list but returns a generator
            itertools.chain(url.path.segments, segments)
        )
    ))
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

    @asyncio.coroutine
    def move(self, dest_provider, src_path, dest_path, rename=None, conflict='replace', handle_naming=True):
        """Moves a file or folder from the current provider to the specified one
        Performs a copy and then a delete.
        Calls :func:`BaseProvider.intra_move` if possible.

        :param BaseProvider dest_provider: The provider to move to
        :param dict source_options: A dict to be sent to either :func:`BaseProvider.intra_move`
            or :func:`BaseProvider.copy` and :func:`BaseProvider.delete`
        :param dict dest_options: A dict to be sent to either :func:`BaseProvider.intra_move`
            or :func:`BaseProvider.copy`
        """
        args = (dest_provider, src_path, dest_path)
        kwargs = {'rename': rename, 'conflict': conflict}

        if handle_naming:
            dest_path = yield from dest_provider.handle_naming(
                src_path,
                dest_path,
                rename=rename,
                conflict=conflict,
            )
            args = (dest_provider, src_path, dest_path)
            kwargs = {}

        if self.can_intra_move(dest_provider, src_path):
            return (yield from self.intra_move(*args))

        if src_path.is_dir:
            metadata, created = yield from self._folder_file_op(self.move, *args, **kwargs)
        else:
            metadata, created = yield from self.copy(*args, handle_naming=False, **kwargs)

        yield from self.delete(src_path)

        return metadata, created

    @asyncio.coroutine
    def copy(self, dest_provider, src_path, dest_path, rename=None, conflict='replace', handle_naming=True):
        args = (dest_provider, src_path, dest_path)
        kwargs = {'rename': rename, 'conflict': conflict, 'handle_naming': handle_naming}

        if handle_naming:
            dest_path = yield from dest_provider.handle_naming(
                src_path,
                dest_path,
                rename=rename,
                conflict=conflict,
            )
            args = (dest_provider, src_path, dest_path)
            kwargs = {}

        if self.can_intra_copy(dest_provider, src_path):
                return (yield from self.intra_copy(*args))

        if src_path.is_dir:
            return (yield from self._folder_file_op(self.copy, *args, **kwargs))

        return (yield from dest_provider.upload(
            (yield from self.download(src_path)),
            dest_path
        ))

    @asyncio.coroutine
    def _folder_file_op(self, func, dest_provider, src_path, dest_path, **kwargs):
        assert src_path.is_dir, 'src_path must be a directory'
        assert asyncio.iscoroutinefunction(func), 'func must be a coroutine'

        try:
            yield from dest_provider.delete(dest_path)
            created = True
        except exceptions.ProviderError as e:
            if e.code != 404:
                raise
            created = False

        folder = yield from dest_provider.create_folder(dest_path)

        dest_path = yield from dest_provider.revalidate_path(dest_path.parent, dest_path.name, folder=dest_path.is_dir)

        futures = []
        for item in (yield from self.metadata(src_path)):
            futures.append(
                asyncio.async(
                    func(
                        dest_provider,
                        # TODO figure out a way to cut down on all the requests made here
                        (yield from self.revalidate_path(src_path, item['name'], folder=item['kind'] == 'folder')),
                        (yield from dest_provider.revalidate_path(dest_path, item['name'], folder=item['kind'] == 'folder')),
                        # src_path.child(item['name'], _id=item.get('id'), folder=item['kind'] == 'folder'),
                        # dest_path.child(item['name'], _id=item.get('id'), folder=item['kind'] == 'folder'),
                        handle_naming=False,
                    )
                )
            )

        if not futures:
            folder['children'] = []
            return folder, created

        finished, pending = yield from asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)

        if len(pending) != 0:
            finished.pop().result()

        folder['children'] = [
            future.result()[0]  # result is a tuple of (metadata, created)
            for future in finished
        ]

        return folder, created

    @asyncio.coroutine
    def handle_naming(self, src_path, dest_path, rename=None, conflict='replace'):
        """Given a WaterButlerPath and the desired name handle any potential
        naming issues

        ie:
            cp /file.txt /folder/ -> /folder/file.txt
            cp /folder/ /folder/ -> /folder/folder/
            cp /file.txt /folder/file.txt -> /folder/file.txt
            cp /file.txt /folder/file.txt -> /folder/file (1).txt
            cp /file.txt /folder/doc.txt -> /folder/doc.txt

        :param WaterButlerPath src_path: The object that is being copied
        :param WaterButlerPath dest_path: The path that is being copied to or into
        :param str rename: The desired name of the resulting path, may be incremented
        :param str conflict: The conflict resolution strategy, replace or keep
        """
        if src_path.is_dir and dest_path.is_file:
            # Cant copy a directory to a file
            raise ValueError('Destination must be a directory if the source is')

        if not dest_path.is_file:
            # Directories always are going to be copied into
            # cp /folder1/ /folder2/ -> /folder1/folder2/
            dest_path = yield from self.revalidate_path(
                dest_path,
                rename or src_path.name,
                folder=src_path.is_dir
            )

        dest_path, _ = yield from self.handle_name_conflict(dest_path, conflict=conflict)

        return dest_path

    def can_intra_copy(self, other, path=None):
        """Indicates if a quick copy can be performed
        between the current and `other`.

        .. note::
            Defaults to False

        :param waterbutler.core.provider.BaseProvider other: The provider to check against
        :rtype: bool
        """
        return False

    def can_intra_move(self, other, path=None):
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
    def intra_move(self, dest_provider, src_path, dest_path):
        data, created = yield from self.intra_copy(dest_provider, src_path, dest_path)
        yield from self.delete(src_path)
        return data, created

    @asyncio.coroutine
    def exists(self, path, **kwargs):
        try:
            return (yield from self.metadata(path, **kwargs))
        except exceptions.NotFoundError:
            return False
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
        :rtype: (WaterButlerPath, dict or False)
        """
        exists = yield from self.exists(path, **kwargs)
        if not exists or conflict != 'keep':
            return path, exists

        while (yield from self.exists(path.increment_name(), **kwargs)):
            pass
        # path.increment_name()
        # exists = self.exists(str(path))
        return path, False

    @asyncio.coroutine
    def revalidate_path(self, base, path, folder=False):
        return base.child(path, folder=folder)

    @asyncio.coroutine
    def zip(self, path, **kwargs):
        """Streams a Zip archive of the given folder

        :param str path: The folder to compress
        """
        if path.is_file:
            base_path = path.parent.path
        else:
            base_path = path.path

        names, coros, remaining = [], [], [path]

        while remaining:
            path = remaining.pop()
            metadata = yield from self.metadata(path)

            for item in metadata:
                current_path = yield from self.revalidate_path(
                    path,
                    item['name'],
                    folder=item['kind'] == 'folder'
                )
                if current_path.is_file:
                    names.append(current_path.path.replace(base_path, '', 1))
                    coros.append(self.__zip_defered_download(current_path))
                else:
                    remaining.append(current_path)

        return streams.ZipStreamReader(*zip(names, coros))

    def __zip_defered_download(self, path):
        """Returns a scoped lambda to defer the execution
        of the download coroutine
        """
        return lambda: self.download(path)

    @abc.abstractmethod
    def download(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def upload(self, stream, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def metadata(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def validate_path(self, path, **kwargs):
        raise NotImplementedError

    def revisions(self, **kwargs):
        return []  # TODO Raise 405 by default h/t @rliebz

    def create_folder(self, *args, **kwargs):
        """Create a folder in the current provider
        returns True if the folder was created; False if it already existed

        :rtype FolderMetadata:
        :raises: waterbutler.ProviderError
        """
        raise exceptions.ProviderError({'message': 'Folder creation not supported.'}, code=405)
