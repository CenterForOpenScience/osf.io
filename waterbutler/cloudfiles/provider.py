import os
import hmac
import json
import time
import asyncio
import hashlib
import functools

import furl

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.cloudfiles import settings
from waterbutler.cloudfiles.metadata import CloudFilesFileMetadata
from waterbutler.cloudfiles.metadata import CloudFilesFolderMetadata
from waterbutler.cloudfiles.metadata import CloudFilesHeaderMetadata


def ensure_connection(func):
    """Runs ``_ensure_connection`` before continuing to the method
    """
    @functools.wraps(func)
    @asyncio.coroutine
    def wrapped(self, *args, **kwargs):
        yield from self._ensure_connection()
        return (yield from func(self, *args, **kwargs))
    return wrapped


class CloudFilesProvider(provider.BaseProvider):
    """Provider for Rackspace CloudFiles
    """
    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = None
        self.endpoint = None
        self.temp_url_key = None
        self.region = self.credentials['region']
        self.og_token = self.credentials['token']
        self.username = self.credentials['username']
        self.container = self.settings['container']

    @property
    def default_headers(self):
        return {
            'X-Auth-Token': self.token,
            'Accept': 'application/json',
        }

    @ensure_connection
    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        source_path = self.format_path(source_options['path'])
        dest_path = self.format_path(dest_options['path'])
        url = dest_provider.build_url(dest_path)
        yield from self.make_request(
            'PUT',
            url,
            headers={
                'X-Copy-From': self.format_path(
                    os.path.join(self.container, source_path.lstrip('/'))  # ensure no left slash when joining paths
                )
            },
            expects=(201, ),
            throws=exceptions.IntraCopyError,
        )
        return (yield from dest_provider.metadata(dest_options['path']))

    @ensure_connection
    @asyncio.coroutine
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseStreamReader (Stream) for the specified path
        :param str path: Path to the object you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype str:
        :rtype ResponseStreamReader:
        :raises: exceptions.DownloadError
        """
        provider_path = self.format_path(path)
        url = self.generate_url(provider_path)

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
    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseStreamReader stream: The stream to put to Cloudfiles
        :param str path: The full path of the object to upload to/into
        :rtype ResponseStreamReader:
        """
        try:
            yield from self.metadata(path, **kwargs)
        except exceptions.MetadataError:
            created = True
        else:
            created = False

        provider_path = self.format_path(path)
        url = self.generate_url(provider_path, 'PUT')
        yield from self.make_request(
            'PUT',
            url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        return (yield from self.metadata(path)), created

    @ensure_connection
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseStreamReader:
        """
        provider_path = self.format_path(path)
        yield from self.make_request(
            'DELETE',
            self.build_url(provider_path),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @ensure_connection
    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        if not path or path.endswith('/'):
            return (yield from self._metadata_folder(path, **kwargs))
        else:
            return (yield from self._metadata_file(path, **kwargs))

    def build_url(self, path):
        """Build the url for the specified object
        :param str path: The stream in question
        :rtype str:
        """
        url = furl.furl(self.endpoint)
        url.path.add(self.container)
        url.path.add(path)
        return url.url

    def can_intra_copy(self, dest_provider):
        return self == dest_provider

    def can_intra_move(self, dest_provider):
        return self == dest_provider

    def format_path(self, path):
        """Validates and converts a WaterButler specific path to a Provider specific path
        :param str path: WaterButler specific path
        :rtype str: Provider specific path
        """
        return super().format_path(path, prefix_slash=False, suffix_slash=True)

    def generate_url(self, path, method='GET', seconds=settings.TEMP_URL_SECS):
        """Build and sign a temp url for the specified stream
        :param str stream: The requested stream's path
        :param str method: The HTTP method used to access the returned url
        :param int seconds: Time for the url to live
        :rtype str:
        """
        method = method.upper()
        expires = str(int(time.time() + seconds))
        url = furl.furl(self.build_url(path))

        body = '\n'.join([method, expires, str(url.path)]).encode()
        signature = hmac.new(self.temp_url_key, body, hashlib.sha1).hexdigest()

        url.args.update({
            'temp_url_sig': signature,
            'temp_url_expires': expires,
        })
        return url.url

    @asyncio.coroutine
    def _ensure_connection(self):
        """Defines token, endpoint and temp_url_key if they are not already defined
        :raises ProviderError: If no temp url key is available
        """
        # Must have a temp url key for download and upload
        # Currently You must have one for everything however
        if not self.token or not self.endpoint or not self.temp_url_key:
            data = yield from self._get_token()
            self.token = data['access']['token']['id']
            self.endpoint = self._extract_endpoint(data)
            resp = yield from self.make_request('HEAD', self.endpoint, expects=(204, ))
            try:
                self.temp_url_key = resp.headers['X-Account-Meta-Temp-URL-Key'].encode()
            except KeyError:
                raise exceptions.ProviderError('No temp url key is available', code=503)

    def _extract_endpoint(self, data):
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

    @asyncio.coroutine
    def _get_token(self):
        """Fetches an access token from cloudfiles for actual api requests
        Returns the entire json response from the tokens endpoint
        Notably containing our token and proper endpoint to send requests to
        :rtype dict:
        """
        resp = yield from self.make_request(
            'POST',
            settings.AUTH_URL,
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

    def _metadata_file(self, path, **kwargs):
        """Get Metadata about the requested file
        :param str path: The path to a key
        :rtype dict:
        :rtype list:
        """
        url = furl.furl(self.build_url(path))
        resp = yield from self.make_request(
            'HEAD',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        return CloudFilesHeaderMetadata(resp.headers, path).serialized()

    def _metadata_folder(self, path, **kwargs):
        """Get Metadata about the requested folder
        :param str path: The path to a folder
        :rtype dict:
        :rtype list:
        """
        provider_path = self.format_path(path)
        url = furl.furl(self.build_url(''))
        url.args.update({'prefix': provider_path, 'delimiter': '/'})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        data = yield from resp.json()

        # no data and the provider path is not root, we are left with either a file or a directory marker
        if not data and provider_path:
            metadata = yield from self._metadata_file(os.path.dirname(path), **kwargs)
            if not metadata:
                raise exceptions.MetadataError(
                    'Could not retrieve folder {0}'.format(path),
                    code=404,
                )

        # normalized metadata, remove extraneous directory markers
        for item in data:
            if 'subdir' in item:
                for marker in data:
                    if 'content_type' in marker and marker['content_type'] == 'application/directory':
                        subdir_path = item['subdir'].rstrip('/')
                        if marker['name'] == subdir_path:
                            data.remove(marker)
                            break

        return [
            self._serialize_folder_metadata(item)
            for item in data
        ]

    def _serialize_folder_metadata(self, data):
        if data.get('subdir'):
            return CloudFilesFolderMetadata(data).serialized()
        elif data['content_type'] == 'application/directory':
            return CloudFilesFolderMetadata({'subdir': data['name'] + '/'}).serialized()
        return CloudFilesFileMetadata(data).serialized()
