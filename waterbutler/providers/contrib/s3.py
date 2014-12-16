import os
import asyncio
import hashlib

from lxml import objectify

from boto.s3.connection import S3Connection

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions


TEMP_URL_SECS = 100


@core.register_provider('s3')
class S3Provider(core.BaseProvider):
    """Provider for the Amazon's S3
    """

    def __init__(self, auth, identity):
        """
        Note: Neither `S3Connection#__init__` nor `S3Connection#get_bucket`
        sends a request.
        :param dict auth: Not used
        :param dict identity: A dict containing access_key secret_key and bucket
        """
        super().__init__(auth, identity)
        self.connection = S3Connection(identity['access_key'], identity['secret_key'])
        self.bucket = self.connection.get_bucket(identity['bucket'], validate=False)

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return type(self) == type(dest_provider)

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        """Copy key from one S3 bucket to another. The identity specified in
        `dest_provider` must have read access to `source.bucket`.
        """
        dest_key = dest_provider.bucket.new_key(dest_options['path'])
        source_path = '/' + os.path.join(self.identity['bucket'], source_options['path'])
        headers = {'x-amz-copy-source': source_path}
        url = dest_key.generate_url(
            TEMP_URL_SECS,
            'PUT',
            headers=headers,
        )
        resp = yield from self.make_request(
            'PUT',
            url,
            headers=headers,
            expects=(200, ),
            throws=exceptions.IntraCopyError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def download(self, path, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        raises FileNotFoundError if the status from S3 is not 200

        :param str path: Path to the key you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        if not path:
            raise exceptions.ProviderError('Path can not be empty', code=400)

        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS)
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
        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'PUT')
        resp = yield from self.make_request(
            'PUT', url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        # md5 is returned as ETag header as long as server side encryption is not used.
        # TODO: nice assertion error goes here
        assert resp.headers['ETag'].replace('"', '') == stream.writers['md5'].hexdigest

        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'DELETE')
        resp = yield from self.make_request(
            'DELETE',
            url,
            expects=(200, 204),
            throws=exceptions.DeleteError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        url = self.bucket.generate_url(TEMP_URL_SECS, 'GET')
        resp = yield from self.make_request(
            'GET',
            url,
            params={'prefix': path, 'delimiter': '/'},
            expects=(200, ),
            throws=exceptions.MetadataError,
        )
        content = yield from resp.read_and_close()
        obj = objectify.fromstring(content)

        files = [
            S3FileMetadata(item).serialized()
            for item in getattr(obj, 'Contents', [])
            if os.path.split(item.Key.text)[1]
        ]

        folders = [
            S3FolderMetadata(item).serialized()
            for item in getattr(obj, 'CommonPrefixes', [])
        ]

        if path[-1] == '/':
            return files + folders

        try:
            return files[0]
        except IndexError:
            raise exceptions.MetadataError(path, code=404)


class S3FileMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 's3'

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return os.path.split(self.raw.Key.text)[1]

    @property
    def path(self):
        return self.raw.Key.text

    @property
    def size(self):
        return self.raw.Size.text

    @property
    def modified(self):
        return self.raw.LastModified.text

    @property
    def extra(self):
        return {
            'md5': self.raw.ETag.text.replace('"', '')
        }


class S3FolderMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 's3'

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw.Prefix.text.split('/')[-2]

    @property
    def path(self):
        return self.raw.Prefix.text

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None
