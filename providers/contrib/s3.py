# encoding: utf-8

import aiohttp

from asyncio import coroutine
from boto.s3.connection import S3Connection

from providers import core
from providers.exceptions import FileNotFoundError


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

    # @coroutine
    # def list(self, **kwargs):
    #     url = self.bucket.generate_url(100, 'GET')
    #     resp = yield from aiohttp.request('GET', url, params=kwargs)
    #
    #     return (yield from self._response_to_dict_list(resp))
    #
    # @coroutine
    # def _response_to_dict_list(self, resp):
    #     # TODO: Fix meand clean me
    #     content = yield from resp.read_and_close()
    #     # parsed = objectify.fromstring(content)
    #     # return parsed
    #     return [{
    #             'md5': fo.ETag,
    #             'last_mod': fo.LastModified,
    #             'full_path': fo.Key,
    #             'size': fo.Size
    #         }
    #         for fo in parsed.Content
    #     ] + [{'prefix': p.Prefix} for p in parsed.get('CommonPrefixes', ())]
