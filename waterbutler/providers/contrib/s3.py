# encoding: utf-8
from asyncio import coroutine

import aiohttp

from boto.s3.connection import S3Connection

from waterbutler.exceptions import FileNotFoundError
from waterbutler.providers import core


@core.register_provider('s3')
class S3Provider(core.BaseProvider):

    def __init__(self, access_key, secret_key, bucket, **kwargs):
        self.connection = S3Connection(access_key, secret_key)
        self.bucket = self.connection.get_bucket(bucket, validate=False)

    @coroutine
    def download(self, path, **kwargs):
        key = self.bucket.new_key(path)
        url = key.generate_url(100)
        resp = yield from aiohttp.request('GET', url)
        if resp.status != 200:
            raise FileNotFoundError(path)

        return core.ResponseWrapper(resp)

    @coroutine
    def upload(self, obj, path):
        key = self.bucket.new_key(path)
        url = key.generate_url(100, 'PUT')
        resp = yield from aiohttp.request(
            'PUT', url,
            data=obj.content,
            headers={'Content-Length': obj.size}
        )

        return core.ResponseWrapper(resp)

    @coroutine
    def delete(self, path):
        key = self.bucket.new_key(path)
        url = key.generate_url(100, 'DELETE')
        resp = yield from aiohttp.request('DELETE', url)

        return resp

    @coroutine
    def metadata(self, path):
        url = self.bucket.generate_url(100, 'GET')
        resp = yield from aiohttp.request('GET', url, params={'prefix': path, 'delimiter': '/'})

        if resp.status_code == 404:
            raise Exception('TODO NOT FOUND ERROR')

        content = yield from resp.read_and_close()
        obj = lxml.objectify(content)

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
            'name': os.path.split(fo.Key)[1],
            'size': fo.Size,
            'path': fo.Key,
            'modified': fo.LastModified,
            'extra': {
                'md5': fo.ETag,
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
