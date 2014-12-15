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

    @core.expects(200, 201, error=exceptions.IntraCopyError)
    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        url = self.build_url(source_options['path'])
        resp = yield from self.make_request(
            'POST', url,
            headers={
                'Destination': os.path.join(dest_provider.container, dest_options['path'])
            },
        )
        if resp.status == 201:
            return True
        raise exceptions.IntraCopyError('Failed to intra copy {} to {}'.format(source_options['path'], dest_options['path']))

    @core.expects(200, error=exceptions.IntraMoveError)
    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        res = yield from self.intra_copy(dest_provider, source_options, dest_options)
        if res:
            yield from self.delete(source_options['path'])
        raise exceptions.IntraMoveError('Failed to intra copy {} to {}'.format(source_options['path'], dest_options['path']))

    @asyncio.coroutine
    def get_token(self):
        """Fetchs an access token from cloudfiles for actual api requests
        Returns the entire json response from the tokens endpoint
        Notably containing our token and proper endpoint to send requests to
        :rtype dict:
        """
        resp = yield from self.make_request(
            'POST',
            'https://identity.api.rackspacecloud.com/v2.0/tokens',
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
            }
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
            resp = yield from self.make_request('HEAD', self.endpoint)
            try:
                self.temp_url_key = resp.headers['X-Account-Meta-Temp-URL-Key'].encode()
            except KeyError:
                raise exceptions.ProviderError('Not temp url key is available', code=503)

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
            if service['name'] == 'cloudFiles':
                for region in service['endpoints']:
                    if region['region'] == self.region:
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

    @core.expects(200, error=exceptions.DownloadError)
    @ensure_connection
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        :param str path: Path to the object you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype str:
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        url = self.generate_url(path)

        if accept_url:
            return url

        resp = yield from self.make_request('GET', url)
        return streams.ResponseStreamReader(resp)

    @core.expects(200, 201, error=exceptions.UploadError)
    @ensure_connection
    def upload(self, stream, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper stream: The stream to put to Cloudfiles
        :param str path: The full path of the object to upload to/into
        :rtype ResponseWrapper:
        """
        url = self.generate_url(path, 'PUT')
        resp = yield from self.make_request(
            'PUT', url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
        )
        return streams.ResponseStreamReader(resp)

    @core.expects(204, error=exceptions.DeleteError)
    @ensure_connection
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        resp = yield from self.make_request('DELETE', self.build_url(path))
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
        resp = yield from self.make_request('GET', url.url)

        if resp.status == 404:
            raise exceptions.FileNotFoundError(path)
        if resp.status == 204:
            return []  # TODO Correct value?

        data = yield from resp.json()

        items = []
        for item in data:
            if item.get('subdir'):
                items.append(CloudFilesFolderMetadata(item).serialized())
            else:
                items.append(CloudFilesFileMetadata(item).serialized())
        return items


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
