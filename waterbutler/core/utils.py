import os
import json
import asyncio
import logging
import functools
# from concurrent.futures import ProcessPoolExecutor  TODO Get this working

import aiohttp

from raven.contrib.tornado import AsyncSentryClient
from stevedore import driver

from waterbutler import settings
from waterbutler.server import settings as server_settings
from waterbutler.core import exceptions
from waterbutler.core.signing import Signer


logger = logging.getLogger(__name__)

sentry_dns = settings.get('SENTRY_DSN', None)
signer = Signer(server_settings.HMAC_SECRET, server_settings.HMAC_ALGORITHM)


class AioSentryClient(AsyncSentryClient):

    def send_remote(self, url, data, headers=None, callback=None):
        headers = headers or {}
        if not self.state.should_try():
            message = self._get_log_message(data)
            self.error_logger.error(message)
            return

        future = aiohttp.request('POST', url, data=data, headers=headers)
        asyncio.async(future)


if sentry_dns:
    client = AioSentryClient(sentry_dns)
else:
    client = None


def make_provider(name, auth, credentials, settings):
    """Returns an instance of :class:`waterbutler.core.provider.BaseProvider`

    :param str name: The name of the provider to instantiate. (s3, box, etc)
    :param dict auth:
    :param dict credentials:
    :param dict settings:

    :rtype: :class:`waterbutler.core.provider.BaseProvider`
    """
    manager = driver.DriverManager(
        namespace='waterbutler.providers',
        name=name,
        invoke_on_load=True,
        invoke_args=(auth, credentials, settings),
    )
    return manager.driver


class WaterButlerPath:
    """
    A standardized and validated immutable WaterButler path.
    """
    def __init__(self, path, prefix=True, suffix=True):
        self._validate_path(path)

        self._orig_path = path
        self._parts = path.rstrip('/').split('/')
        self._is_dir = path.endswith('/')
        self._is_root = path == '/'
        self._prefix = prefix
        self._suffix = suffix

        # after class variables have been setup
        self._path = self._format_path(path)
        # For name confliction resolution
        # foo.txt -> foo (1).txt -> foo (2).txt
        self._count = 0
        self._orig_name = self.name

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._orig_path)

    def __str__(self):
        return self._orig_path

    @property
    def path(self):
        return self._path

    @property
    def is_dir(self):
        return self._is_dir

    @property
    def is_file(self):
        return not self._is_dir

    @property
    def is_root(self):
        return self._is_root

    @property
    def is_leaf(self):
        """If this path has no child paths.

        * True if:
            * Folder with no children ("/")
            * File with no children ("/path.txt")
        * False if:
            * Folder with children ("/foo/")
            * File with children ("/foo/path.txt")
        """
        parts = [each for each in self.parts if each]
        return len(parts) == 0 if self.is_dir else len(parts) == 1

    @property
    def name(self):
        return self._parts[-1]

    def increment_name(self):
        self._count += 1
        name, ext = os.path.splitext(self._orig_name)
        new_name = '{} ({}){}'.format(name, self._count, ext)
        self._orig_path = self._orig_path.replace(self.name, new_name)
        self._parts[-1] = new_name
        self._path = self._format_path(self._orig_path)
        return self

    @property
    def parts(self):
        return self._parts

    @property
    def parent(self):
        cls = self.__class__
        return cls('/'.join(self._parts[:-1]) + '/', prefix=self._prefix, suffix=self._suffix)

    @property
    def child(self):
        cls = self.__class__
        path = '/' + '/'.join(self._parts[2:])
        if self.is_dir:
            path += '/'
        path = path.replace('//', '/')
        return cls(path, prefix=self._prefix, suffix=self._suffix)

    def _format_path(self, path):
        """Formats the specified path per the class configuration prefix/suffix configuration.
        :param str path: WaterButler specific path
        :rtype str: Provider specific path
        """
        # Display root as '/' if prefix is true
        if not self._prefix:
            path = path.lstrip('/')
        if path and path != '/':
            if not self._suffix:
                path = path.rstrip('/')
        return path

    def _validate_path(self, path):
        """Validates a WaterButler specific path, e.g. /folder/file.txt, /folder/
        :param str path: WaterButler path
        """
        if not path:
            raise exceptions.InvalidPathError('Must specify path')
        if not path.startswith('/'):
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        if '//' in path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        # Do not allow path manipulation via shortcuts, e.g. '..'
        absolute_path = os.path.abspath(path)
        if not path == '/' and path.endswith('/'):
            absolute_path += '/'
        if not path == absolute_path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(absolute_path))

    def validate_folder(self):
        """Raise CreateFolderErrors if the folder path is invalid
        :returns: None
        :raises: waterbutler.CreateFolderError
        """
        if not self.is_dir:
            raise exceptions.CreateFolderError('Path must be a directory', code=400)

        if self.path == '/':
            raise exceptions.CreateFolderError('Path can not be root', code=400)


def as_task(func):
    if not asyncio.iscoroutinefunction(func):
        func = asyncio.coroutine(func)

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return asyncio.async(func(*args, **kwargs))

    return wrapped


def async_retry(retries=5, backoff=1, exceptions=(Exception, ), raven=client):

    def _async_retry(func):

        @as_task
        @functools.wraps(func)
        def wrapped(*args, __retries=0, **kwargs):
            try:
                return (yield from asyncio.coroutine(func)(*args, **kwargs))
            except exceptions as e:
                if __retries < retries:
                    wait_time = backoff * __retries
                    logger.warning('Task {0} failed, {1} / {2} retries. Waiting {3} seconds before retrying'.format(func, __retries, retries, wait_time))

                    yield from asyncio.sleep(wait_time)
                    return wrapped(*args, __retries=__retries + 1, **kwargs)
                else:
                    # Logs before all things
                    logger.error('Task {0} failed with exception {1}'.format(func, e))

                    if raven:
                        # Only log if a raven client exists
                        client.captureException()

                    # If anything happens to be listening
                    raise e

        # Retries must be 0 to start with
        # functools partials dont preserve docstrings
        return wrapped

    return _async_retry


@asyncio.coroutine
def send_signed_request(method, url, payload):
    message, signature = signer.sign_payload(payload)
    return (yield from aiohttp.request(
        method, url,
        data=json.dumps({
            'payload': message.decode(),
            'signature': signature,
        }),
        headers={'Content-Type': 'application/json'},
    ))
