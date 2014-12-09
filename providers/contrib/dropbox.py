# encoding: utf-8

import os.path
from asyncio import coroutine

import aiohttp

from webargs import Arg

from providers import core


@core.register_provider('dropbox')
class DropboxProvider(core.BaseProvider):

    def __init__(self, token, folder, **kwargs):
        self.token = token
        self.folder = folder

    def __eq__(self, other):
        try:
            return (
                type(self) == type(other) and
                self.token == other.token and self.folder == other.folder
            )
        except AttributeError:
            return False

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return self == dest_provider

    @coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        url = 'https://api.dropbox.com/1/fileops/copy'
        from_path = os.path.join(self.folder, source_options['path'])
        to_path = os.path.join(dest_provider.folder, dest_options['path'])
        if self == dest_provider:
            # intra copy within the same account
            yield from aiohttp.request('POST', url, data={
                'folder': 'auto',
                'from_path': from_path,
                'to_path': to_path,
            }, headers=self._headers())
        else:
            # create from_copy_ref and use with destination provider
            copy_ref_url = 'https://api.dropbox.com/1/copy_ref/auto/{}'.format(from_path)
            copy_ref_resp = yield from aiohttp.request('GET', copy_ref_url, headers=self._headers())
            from_copy_ref = (yield from copy_ref_resp.content.json()).copy_ref
            yield from aiohttp.request('POST', data={
                'folder': 'auto',
                'from_copy_ref': from_copy_ref,
                'to_path': to_path
            }, headers=dest_provider._headers())

    @coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        url = 'https://api.dropbox.com/1/fileops/move'
        from_path = os.path.join(self.folder, source_options['path'])
        to_path = os.path.join(dest_provider.folder, dest_options['path'])
        yield from aiohttp.request('POST', url, data={
            'folder': 'auto',
            'from_path': from_path,
            'to_path': to_path,
        }, headers=self._headers())

    @coroutine
    def download(self, path, revision=None, **kwargs):
        full_path = os.path.join(self.folder, path)
        url = 'https://api-content.dropbox.com/1/files/auto/{}'.format(full_path)
        resp = yield from aiohttp.request('GET', url, headers=self._headers())
        return core.ResponseWrapper(resp)

    @coroutine
    def upload(self, obj, path):
        full_path = os.path.join(self.folder, path)
        url = 'https://api-content.dropbox.com/1/files_put/auto/{}'.format(full_path)
        resp = yield from aiohttp.request('PUT', url, data=obj.content, headers=self._headers(**{'Content-Length': obj.size}))
        return core.ResponseWrapper(resp)

    @coroutine
    def delete(self, path):
        full_path = os.path.join(self.folder, path)
        url = 'https://api.dropbox.com/1/fileops/delete'
        resp = yield from aiohttp.request('POST', url, data={'folder': 'auto', 'path': full_path}, headers=self._headers())
        return resp

    @coroutine
    def metadata(self, path):
        full_path = os.path.join(self.folder, path)
        url = 'https://api.dropbox.com/1/metadata/auto/{}'.format(full_path)
        resp = yield from aiohttp.request('GET', url, headers=self._headers())
        return resp

    def _headers(self, **kwargs):
        headers = {
            'authorization': 'Bearer {}'.format(self.token),
        }
        headers.update({
            key: value for key, value in kwargs.items()
            if value is not None
        })
        return headers
