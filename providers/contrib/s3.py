# encoding: utf-8

import aiohttp

from asyncio import coroutine
from boto.s3.connection import S3Connection
from providers import core


class S3Provider(core.BaseProvider):

    def __init__(self, access_key, secret_key, bucket, **kwargs):
        self.connection = S3Connection(access_key, secret_key)
        self.bucket = self.connection.get_bucket(bucket, validate=False)

    @coroutine
    def download(self, path):
        key = self.bucket.new_key(path)
        url = key.generate_url(100)
        resp = yield from aiohttp.request('GET', url)
        return core.ResponseWrapper(resp)

    @coroutine
    def upload(self, obj, path):
        key = self.bucket.new_key(path)
        url = key.generate_url(100, 'PUT')
        resp = yield from aiohttp.request('PUT', url, data=obj.content, headers={'Content-Length': obj.size})
        return core.ResponseWrapper(resp)

    # @coroutine
    def delete(self, path):
        # TODO: implement delete
        pass
