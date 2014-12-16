import os
import hmac
import json
import time
import asyncio
import hashlib
import functools

import furl

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions


TEMP_URL_SECS = 100
AUTH_URL = 'https://identity.api.rackspacecloud.com/v2.0/tokens'


def ensure_connection(func):
    """Runs ``_ensure_connection`` before continuing to the method
    """
    @functools.wraps(func)
    @asyncio.coroutine
    def wrapped(self, *args, **kwargs):
        yield from self._ensure_connection()
        return (yield from func(self, *args, **kwargs))
    return wrapped


def format_metadata(data):
    if data.get('subdir'):
        return {
            'name': data['subdir'],
            'path': data['subdir'],
        }
    else:
        return {
            'name': os.path.split(data['name'])[1],
            'path': data['name'],
            'size': data['bytes'],
            'modified': data['last_modified'],
        }


@core.register_provider('cloudfiles')
class CloudFilesProvider(core.BaseProvider):
    """Provider for Rackspace CloudFiles
    """

    def __init__(self, auth, identity):
        super().__init__(auth, identity)
        self.token = None
        self.endpoint = None
        self.temp_url_key = None
        self.region = self.identity['region']
        self.og_token = self.identity['token']
        self.username = self.identity['username']
        self.container = self.identity['container']

    def can_intra_copy(self, dest_provider):
        return self == dest_provider

    def can_intra_move(self, dest_provider):
        return self == dest_provider

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        url = dest_provider.build_url(dest_options['path'])
        resp = yield from self.make_request(
            'PUT',
            url,
            headers={
                'X-Copy-From': os.path.join(self.container, source_options['path'])
            },
            expects=(201, ),
            throws=exceptions.IntraCopyError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def get_token(self):
        """Fetchs an access token from cloudfiles for actual api requests
        Returns the entire json response from the tokens endpoint
        Notably containing our token and proper endpoint to send requests to
        :rtype dict:
        """
        resp = yield from self.make_request(
            'POST',
            AUTH_URL,
            data=json.dumps({
                'auth': {
                    'RAX-KSKEY:apiKeyCredentials': {
                        'username': self.username,
                        'apiKey': self.og_token,
                    }
                }
            }),
            headers={
                'Content-Type': 'application/json',
            },
            expects=(200, ),
        )
        data = yield from resp.json()
        return data

    @asyncio.coroutine
    def _ensure_connection(self):
        """Defines token, endpoint and temp_url_key if they are not already defined
        :raises ProviderError: If no temp url key is available
        """
        # Must have a temp url key for download and upload
        # Currently You must have one for everything however
        if not self.token or not self.endpoint or not self.temp_url_key:
            data = yield from self.get_token()
            self.token = data['access']['token']['id']
            self.endpoint = self.extract_endpoint(data)
            resp = yield from self.make_request('HEAD', self.endpoint, expects=(204 ,))
            try:
                self.temp_url_key = resp.headers['X-Account-Meta-Temp-URL-Key'].encode()
            except KeyError:
                raise exceptions.ProviderError('No temp url key is available', code=503)

    @property
    def default_headers(self):
        return {
            'X-Auth-Token': self.token,
            'Accept': 'application/json',
        }

    def extract_endpoint(self, data):
        """Pulls the proper cloudfiles url from the return of tokens
        Very optimized.
        :param dict data: The json response from the token endpoint
        :rtype str:
        """
        for service in reversed(data['access']['serviceCatalog']):
            if service['name'].lower() == 'cloudfiles':
                for region in service['endpoints']:
                    if region['region'].lower() == self.region.lower():
                        return region['publicURL']

    def build_url(self, stream):
        """Build the url for the specified object
        :param str stream: The stream in question
        :rtype str:
        """
        url = furl.furl(self.endpoint)
        url.path.add(self.container)
        url.path.add(stream)
        return url.url

    def generate_url(self, stream, method='GET', seconds=60):
        """Build and sign a temp url for the specified stream
        :param str stream: The requested stream's path
        :param str method: The HTTP method used to access the returned url
        :param int seconds: Time for the url to live
        :rtype str:
        """
        method = method.upper()
        expires = str(int(time.time() + seconds))
        url = furl.furl(self.build_url(stream))

        body = '\n'.join([method, expires, str(url.path)]).encode()
        signature = hmac.new(self.temp_url_key, body, hashlib.sha1).hexdigest()

        url.args.update({
            'temp_url_sig': signature,
            'temp_url_expires': expires,
        })
        return url.url

    @ensure_connection
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseStreamReader (Stream) for the specified path
        :param str path: Path to the object you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype str:
        :rtype ResponseStreamReader:
        :raises: waterbutler.FileNotFoundError
        """
        url = self.generate_url(path)

        if accept_url:
            return url

        resp = yield from self.make_request(
            'GET',
            url,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @ensure_connection
    def upload(self, stream, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseStreamReader stream: The stream to put to Cloudfiles
        :param str path: The full path of the object to upload to/into
        :rtype ResponseStreamReader:
        """
        url = self.generate_url(path, 'PUT')
        yield from self.make_request(
            'PUT',
            url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        return (yield from self.metadata(path))

    @ensure_connection
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseStreamReader:
        """
        resp = yield from self.make_request(
            'DELETE',
            self.build_url(path),
            excepts=(204, ),
            throws=exceptions.DeleteError,
        )
        return streams.ResponseStreamReader(resp)

    @ensure_connection
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        url = furl.furl(self.build_url(''))
        url.args.update({'prefix': path, 'delimiter': '/'})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, 204),
            throws=exceptions.MetadataError,
        )

        data = yield from resp.json()

        if not data:
            raise exceptions.MetadataError(
                'Could not retrieve file or directory {0}'.format(path),
                code=404,
            )

        if path.endswith('/'):
            return [self._serialize_metadata(item) for item in data]
        if data:
            return self._serialize_metadata(data[0])

    def _serialize_metadata(self, metadata):
        if metadata.get('subdir'):
            return CloudFilesFolderMetadata(metadata).serialized()
        return CloudFilesFileMetadata(metadata).serialized()


class CloudFilesFileMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return os.path.split(self.raw['name'])[1]

    @property
    def path(self):
        return self.raw['name']

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['last_modified']


class CloudFilesFolderMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw['subdir']

    @property
    def path(self):
        return self.raw['subdir']

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None
