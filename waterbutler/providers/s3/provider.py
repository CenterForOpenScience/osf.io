import os
import asyncio
import hashlib

import xmltodict

from boto.s3.connection import S3Connection
from boto.s3.connection import OrdinaryCallingFormat

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.s3 import settings
from waterbutler.providers.s3.metadata import S3Revision
from waterbutler.providers.s3.metadata import S3FileMetadata
from waterbutler.providers.s3.metadata import S3FolderMetadata
from waterbutler.providers.s3.metadata import S3FolderKeyMetadata
from waterbutler.providers.s3.metadata import S3FileMetadataHeaders


class S3Path(utils.WaterButlerPath):

    def __init__(self, path, prefix=False, suffix=True):
        super().__init__(path, prefix=prefix, suffix=suffix)


class S3Provider(provider.BaseProvider):
    """Provider for the Amazon's S3
    """

    def __init__(self, auth, credentials, settings):
        """
        Note: Neither `S3Connection#__init__` nor `S3Connection#get_bucket`
        sends a request.
        :param dict auth: Not used
        :param dict credentials: Dict containing `access_key` and `secret_key`
        :param dict settings: Dict containing `bucket`
        """
        super().__init__(auth, credentials, settings)
        self.connection = S3Connection(credentials['access_key'],
                credentials['secret_key'], calling_format=OrdinaryCallingFormat())
        self.bucket = self.connection.get_bucket(settings['bucket'], validate=False)

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return type(self) == type(dest_provider)

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        """Copy key from one S3 bucket to another. The credentials specified in
        `dest_provider` must have read access to `source.bucket`.
        """
        source_path = S3Path(source_options['path'])
        dest_path = S3Path(dest_options['path'])
        dest_key = dest_provider.bucket.new_key(dest_path.path)
        # ensure no left slash when joining paths
        source_path = '/' + os.path.join(self.settings['bucket'], source_options['path'].lstrip('/'))
        headers = {'x-amz-copy-source': source_path}
        url = dest_key.generate_url(
            settings.TEMP_URL_SECS,
            'PUT',
            headers=headers,
        )
        yield from self.make_request(
            'PUT',
            url,
            headers=headers,
            expects=(200, ),
            throws=exceptions.IntraCopyError,
        )
        return (yield from dest_provider.metadata(dest_options['path']))

    @asyncio.coroutine
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        raises FileNotFoundError if the status from S3 is not 200

        :param str path: Path to the key you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        path = S3Path(path)

        if not path.is_file:
            raise exceptions.DownloadError('No file specified for download', code=400)

        key = self.bucket.new_key(path.path)
        url = key.generate_url(settings.TEMP_URL_SECS, response_headers={'response-content-disposition': 'attachment'})
        if accept_url:
            return url
        resp = yield from self.make_request(
            'GET',
            url,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper stream: The stream to put to S3
        :param str path: The full path of the key to upload to/into
        :rtype ResponseWrapper:
        """
        path = S3Path(path)

        try:
            yield from self.metadata(str(path), **kwargs)
        except exceptions.MetadataError:
            created = True
        else:
            created = False

        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        key = self.bucket.new_key(path.path)
        url = key.generate_url(settings.TEMP_URL_SECS, 'PUT')
        resp = yield from self.make_request(
            'PUT', url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
            expects=(200, 201, ),
            throws=exceptions.UploadError,
        )
        # md5 is returned as ETag header as long as server side encryption is not used.
        # TODO: nice assertion error goes here
        assert resp.headers['ETag'].replace('"', '') == stream.writers['md5'].hexdigest

        return (yield from self.metadata(str(path), **kwargs)), created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        path = S3Path(path)
        key = self.bucket.new_key(path.path)
        url = key.generate_url(settings.TEMP_URL_SECS, 'DELETE')
        yield from self.make_request(
            'DELETE',
            url,
            expects=(200, 204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        """Get past versions of the requested key
        :param str path: The path to a key
        :rtype list:
        """
        path = S3Path(path)
        url = self.bucket.generate_url(settings.TEMP_URL_SECS, 'GET', query_parameters={'versions': ''})
        resp = yield from self.make_request(
            'GET',
            url,
            params={'prefix': path.path, 'delimiter': '/'},
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        content = yield from resp.read_and_close()
        obj = xmltodict.parse(content)['ListVersionsResult']
        return [
            S3Revision(path.path, item).serialized()
            for item in obj.get('Version', [])
        ]

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        path = S3Path(path)

        if path.is_dir:
            return (yield from self._metadata_folder(path))

        return (yield from self._metadata_file(path))

    @asyncio.coroutine
    def _metadata_file(self, path):
        url = self.bucket.new_key(path.path).generate_url(settings.TEMP_URL_SECS, 'HEAD')
        resp = yield from self.make_request(
            'HEAD',
            url,
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        return S3FileMetadataHeaders(path.path, resp.headers).serialized()

    @asyncio.coroutine
    def _metadata_folder(self, path):
        url = self.bucket.generate_url(settings.TEMP_URL_SECS, 'GET')
        resp = yield from self.make_request(
            'GET',
            url,
            params={'prefix': path.path, 'delimiter': '/'},
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        contents = yield from resp.read_and_close()

        parsed = xmltodict.parse(contents)['ListBucketResult']

        contents = parsed.get('Contents', [])
        prefixes = parsed.get('CommonPrefixes', [])

        if isinstance(contents, dict):
            contents = [contents]

        if isinstance(prefixes, dict):
            prefixes = [prefixes]

        items = [
            S3FolderMetadata(item).serialized()
            for item in prefixes
        ]

        for content in contents:
            if content['Key'] == path.path:
                continue

            if content['Key'].endswith('/'):
                items.append(S3FolderKeyMetadata(content).serialized())
            else:
                items.append(S3FileMetadata(content).serialized())

        return items
