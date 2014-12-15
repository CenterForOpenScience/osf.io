import os
import asyncio
import hashlib

from lxml import objectify

from boto.s3.connection import S3Connection

from waterbutler import exceptions
from waterbutler.providers import core


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

    @core.expects(200)
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
        resp = yield from self.make_request('GET', url)
        if resp.status != 200:
            raise exceptions.FileNotFoundError(path)

        return core.ResponseStreamReader(resp)

    @core.expects(200, 201)
    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper stream: The stream to put to S3
        :param str path: The full path of the key to upload to/into
        :rtype ResponseWrapper:
        """
        stream.add_writer('md5', core.HashStreamWriter(hashlib.md5))
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'PUT')
        resp = yield from self.make_request(
            'PUT', url,
            data=stream,
            headers={'Content-Length': str(stream.size)},
        )
        # md5 is returned as ETag header as long as server side encryption is not used.
        # TODO: nice assertion error goes here
        assert resp.headers['ETag'].replace('"', '') == stream.writers['md5'].hexdigest

        return core.ResponseStreamReader(resp)

    @core.expects(200, 204)
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'DELETE')
        resp = yield from self.make_request('DELETE', url)

        return core.ResponseStreamReader(resp)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        url = self.bucket.generate_url(TEMP_URL_SECS, 'GET')
        resp = yield from self.make_request('GET', url, params={'prefix': path, 'delimiter': '/'})

        if resp.status == 404:
            raise exceptions.FileNotFoundError(path)

        content = yield from resp.read_and_close()
        obj = objectify.fromstring(content)

        files = [
            self.key_to_dict(k)
            for k in getattr(obj, 'Contents', [])
        ]

        folders = [
            self.prefix_to_dict(p)
            for p in getattr(obj, 'CommonPrefixes', [])
        ]

        if len(folders) == 0 and len(files) == 1:
            return files[0]

        return files + folders

    def key_to_dict(self, key, children=[]):
        return {
            'content': children,
            'provider': 's3',
            'kind': 'file',
            'name': os.path.split(key.Key.text)[1],
            'size': key.Size.text,
            'path': key.Key.text,
            'modified': key.LastModified.text,
            'extra': {
                'md5': key.ETag.text.replace('"', ''),
            },
        }

    def prefix_to_dict(self, prefix, children=[]):
        return {
            'contents': children,
            'provider': 's3',
            'kind': 'folder',
            'name': prefix.Prefix.text.split('/')[-2],
            'path': prefix.Prefix.text,
            'modified': None,
            'size': None,
            'extra': {},
        }
