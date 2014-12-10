# -*- coding: utf-8 -*-

import os
import asyncio

import aiohttp
from lxml import objectify

from boto.s3.connection import S3Connection

from waterbutler.exceptions import FileNotFoundError
from waterbutler.providers import core


@core.register_provider('s3')
class S3Provider(core.BaseProvider):
    """Provider for the Amazon's S3
    """

    def __init__(self, identity, auth):
        """
        """
        self.connection = S3Connection(auth['access_key'], auth['secret_key'])
        self.bucket = self.connection.get_bucket(auth['bucket'], validate=False)

    @asyncio.coroutine
    def download(self, path, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        raises FileNotFoundError if the status from S3 is not 200

        :param str path: Path to the key you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(100)
        resp = yield from aiohttp.request('GET', url)
        if resp.status != 200:
            raise FileNotFoundError(path)

        return core.ResponseWrapper(resp)

    @asyncio.coroutine
    def upload(self, obj, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper obj: The stream to put to S3
        :param str path: The full path of the key to upload to/into
        :rtype ResponseWrapper:
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(100, 'PUT')
        resp = yield from aiohttp.request(
            'PUT', url,
            data=obj.content,
            headers={'Content-Length': obj.size}
        )

        return core.ResponseWrapper(resp)

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        key = self.bucket.new_key(path)
        url = key.generate_url(100, 'DELETE')
        resp = yield from aiohttp.request('DELETE', url)

        return resp

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        url = self.bucket.generate_url(100, 'GET')
        resp = yield from aiohttp.request('GET', url, params={'prefix': path, 'delimiter': '/'})

        if resp.status == 404:
            raise Exception('TODO NOT FOUND ERROR')

        content = yield from resp.read_and_close()
        obj = objectify.fromstring(content)

        files = [
            self.key_to_dict(k)
            for k in getattr(obj, 'Contents', [])
        ]

        folders = [
            self.key_to_dict(p)
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
                'md5': key.ETag.text,
            }
        }

    def prefix_to_dict(self, prefix, children=[]):
        def getname(st):
            sp = st.split('/')
            if not sp[-1]:
                return sp[-2]
            return sp[-1]

        return {
            'contents': children,
            'provider': 's3',
            'kind': 'folder',
            'name': getname(prefix.Prefix),
            'path': prefix.Prefix,
            'modified': None,
            'size': None,
            'extra': {}
        }
