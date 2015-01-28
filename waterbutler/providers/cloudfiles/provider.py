import os
import hmac
import json
import time
import asyncio
import hashlib
import functools

import furl

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.cloudfiles import settings
from waterbutler.providers.cloudfiles.metadata import CloudFilesFileMetadata
from waterbutler.providers.cloudfiles.metadata import CloudFilesFolderMetadata
from waterbutler.providers.cloudfiles.metadata import CloudFilesHeaderMetadata


def ensure_connection(func):
    """Runs ``_ensure_connection`` before continuing to the method
    """
    @functools.wraps(func)
    @asyncio.coroutine
    def wrapped(self, *args, **kwargs):
        yield from self._ensure_connection()
        return (yield from func(self, *args, **kwargs))
    return wrapped


class CloudFilesPath(utils.WaterButlerPath):

    def __init__(self, path, prefix=False, suffix=True):
        super().__init__(path, prefix=prefix, suffix=suffix)


class CloudFilesProvider(provider.BaseProvider):
    """Provider for Rackspace CloudFiles
    """
    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = None
        self.endpoint = None
        self.public_endpoint = None
        self.temp_url_key = credentials.get('temp_key', '').encode()
        self.region = self.credentials['region']
        self.og_token = self.credentials['token']
        self.username = self.credentials['username']
        self.container = self.settings['container']
        self.use_public = self.settings.get('use_public', True)

    @property
    def default_headers(self):
        return {
            'X-Auth-Token': self.token,
            'Accept': 'application/json',
        }

    @ensure_connection
    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        source_path = CloudFilesPath(source_options['path'])
        dest_path = CloudFilesPath(dest_options['path'])
        url = dest_provider.build_url(dest_path.path)
        yield from self.make_request(
            'PUT',
            url,
            headers={
                'X-Copy-From': os.path.join(self.container, source_path.path)
            },
            expects=(201, ),
            throws=exceptions.IntraCopyError,
        )
        return (yield from dest_provider.metadata(str(dest_path)))

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
        path = CloudFilesPath(path)

        if accept_url:
            parsed_url = furl.furl(self.sign_url(path, endpoint=self.public_endpoint))
            parsed_url.args['filename'] = kwargs.get('displayName') or path.name
            return parsed_url.url

        resp = yield from self.make_request(
            'GET',
            self.sign_url(path),
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @ensure_connection
    @asyncio.coroutine
    def upload(self, stream, path, check_created=True, fetch_metadata=True, **kwargs):
        """Uploads the given stream to CloudFiles
        :param ResponseStreamReader stream: The stream to put to CloudFiles
        :param str path: The full path of the object to upload to/into
        :rtype ResponseStreamReader:
        """
        path = CloudFilesPath(path)

        if check_created:
            try:
                yield from self.metadata(str(path), **kwargs)
            except exceptions.MetadataError:
                created = True
            else:
                created = False
        else:
            created = None

        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        url = self.sign_url(path, 'PUT')
        resp = yield from self.make_request(
            'PUT',
            url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        # md5 is returned as ETag header as long as server side encryption is not used.
        # TODO: nice assertion error goes here
        assert resp.headers['ETag'].replace('"', '') == stream.writers['md5'].hexdigest

        if fetch_metadata:
            metadata = yield from self.metadata(str(path))
        else:
            metadata = None

        return metadata, created

    @ensure_connection
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseStreamReader:
        """
        path = CloudFilesPath(path)
        if path.is_dir:
            metadata = yield from self.metadata(str(path), recursive=True)
            delete_files = [
                os.path.join('/', self.container, CloudFilesPath(item['path'], suffix=False).path)
                for item in metadata
            ]
            delete_files.append(os.path.join('/', self.container, CloudFilesPath(str(path), suffix=False).path))

            query = {'bulk-delete': ''}
            yield from self.make_request(
                'DELETE',
                self.build_url(**query),
                data='\n'.join(delete_files),
                expects=(200, ),
                throws=exceptions.DeleteError,
                headers={
                    'Content-Type': 'text/plain',
                },
            )
        else:
            yield from self.make_request(
                'DELETE',
                self.build_url(path.path),
                expects=(204, ),
                throws=exceptions.DeleteError,
            )

    @ensure_connection
    @asyncio.coroutine
    def metadata(self, path, recursive=False, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        path = CloudFilesPath(path)
        if path.is_dir:
            return (yield from self._metadata_folder(path, recursive=recursive, **kwargs))
        else:
            return (yield from self._metadata_file(path, **kwargs))

    def build_url(self, *segments, _endpoint=None, **query):
        """Build the url for the specified object
        :param args segments: URI segments
        :param kwargs query: Query parameters
        :rtype str:
        """
        endpoint = _endpoint or self.endpoint
        return provider.build_url(endpoint, self.container, *segments, **query)

    def can_intra_copy(self, dest_provider):
        return self is dest_provider

    def can_intra_move(self, dest_provider):
        return self.can_intra_copy(dest_provider)

    def sign_url(self, path, method='GET', endpoint=None, seconds=settings.TEMP_URL_SECS):
        """Sign a temp url for the specified stream
        :param str stream: The requested stream's path
        :param CloudFilesPath path: A path to a file/folder
        :param str method: The HTTP method used to access the returned url
        :param int seconds: Time for the url to live
        :rtype str:
        """
        method = method.upper()
        expires = str(int(time.time() + seconds))
        url = furl.furl(self.build_url(path.path, _endpoint=endpoint))

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
        if not self.token or not self.endpoint:
            data = yield from self._get_token()
            self.token = data['access']['token']['id']
            if self.use_public:
                self.public_endpoint, _ = self._extract_endpoints(data)
                self.endpoint = self.public_endpoint
            else:
                self.public_endpoint, self.endpoint = self._extract_endpoints(data)
        if not self.temp_url_key:
            resp = yield from self.make_request('HEAD', self.endpoint, expects=(204, ))
            try:
                self.temp_url_key = resp.headers['X-Account-Meta-Temp-URL-Key'].encode()
            except KeyError:
                raise exceptions.ProviderError('No temp url key is available', code=503)

    def _extract_endpoints(self, data):
        """Pulls both the public and internal cloudfiles urls,
        returned respectively, from the return of tokens
        Very optimized.
        :param dict data: The json response from the token endpoint
        :rtype (str, str):
        """
        for service in reversed(data['access']['serviceCatalog']):
            if service['name'].lower() == 'cloudfiles':
                for region in service['endpoints']:
                    if region['region'].lower() == self.region.lower():
                        return region['publicURL'], region['internalURL']

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

    def _metadata_file(self, path, is_folder=False, **kwargs):
        """Get Metadata about the requested file
        :param str path: The path to a key
        :rtype dict:
        :rtype list:
        """
        resp = yield from self.make_request(
            'HEAD',
            self.build_url(path.path),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )

        if (resp.headers['Content-Type'] == 'application/directory' and not is_folder):
            raise exceptions.MetadataError(
                'Could not retrieve file \'{0}\''.format(path),
                code=404,
            )

        return CloudFilesHeaderMetadata(resp.headers, path.path).serialized()

    def _metadata_folder(self, path, recursive=False, **kwargs):
        """Get Metadata about the requested folder
        :param str path: The path to a folder
        :rtype dict:
        :rtype list:
        """
        # prefix must be blank when searching the root of the container
        query = {'prefix': path.path}
        if not recursive:
            query.update({'delimiter': '/'})
        resp = yield from self.make_request(
            'GET',
            self.build_url('', **query),
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        data = yield from resp.json()

        # no data and the provider path is not root, we are left with either a file or a directory marker
        if not data and not path.is_root:
            # Convert the parent path into a directory marker (file) and check for an empty folder
            dir_marker = CloudFilesPath(str(path).rstrip('/'))
            metadata = yield from self._metadata_file(dir_marker, is_folder=True, **kwargs)
            if not metadata:
                raise exceptions.MetadataError(
                    'Could not retrieve folder \'{0}\''.format(path),
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
