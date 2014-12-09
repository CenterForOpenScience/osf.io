# -*- coding: utf-8 -*-

import os
import json
import base64
from asyncio import coroutine

import furl
import aiohttp

from waterbutler.providers import core


class GithubProvider(core.BaseProvider):

    BASE_URL = 'https://api.github.com/'

    def __init__(self, token, owner, repo):
        self.token = token
        self.owner = owner
        self.repo = repo

    def build_url(self, *segments, **query):
        url = furl.furl(self.BASE_URL)
        url.path = os.path.join(*segments)
        url.args = query
        return url.url

    def build_headers(self, extra=None):
        headers = {'Authorization': 'token {}'.format(self.token)}
        headers.update(extra or {})
        return headers

    @coroutine
    def metadata(self, path, ref=None):
        url = self.build_url('repos', self.owner, self.repo, 'contents', path)
        response = yield from aiohttp.request('GET', url, headers=self.build_headers())
        data = yield from response.json()
        return [
            self._serialize_metadata(item)
            for item in data
        ]

    def _serialize_metadata(self, item):
        return {
            'provider': 'github',
            'kind': 'file' if item['type'] == 'file' else 'folder',
            'name': item['name'],
            'path': item['path'],
            'size': item['size'],
            'modified': None,
            'extra': {
                'sha': item['sha'],
            },
        }

    @coroutine
    def download(self, path, sha):
        url = self.build_url('repos', self.owner, self.repo, 'git', 'blobs', sha)
        headers = self.build_headers({'Accept': 'application/vnd.github.VERSION.raw'})
        response = yield from aiohttp.request('GET', url, headers=headers)
        return core.ResponseWrapper(response)

    @coroutine
    def upload(self, obj, path, message, committer, branch=None):
        content = yield from obj.content.read()
        encoded = base64.b64encode(content)
        data = {
            'path': path,
            'message': message,
            'content': encoded.decode('utf-8'),
            'committer': committer,
        }
        if branch is not None:
            data['branch'] = branch
        # Check whether file already exists in tree; if it does, add the SHA
        # to the payload. This changes the call from a create to an update.
        tree = yield from self.metadata(os.path.dirname(path), ref=branch)
        existing = next(
            (each for each in tree if each['path'] == path),
            None
        )
        if existing:
            data['sha'] = existing['extra']['sha']
        url = self.build_url('repos', self.owner, self.repo, 'contents', path)
        response = yield from aiohttp.request('PUT', url, data=json.dumps(data), headers=self.build_headers())
        return core.ResponseWrapper(response)

    @coroutine
    def delete(self, path, message, sha, committer, branch=None):
        url = self.build_url('repos', self.owner, self.repo, 'contents', path)
        data = {
            'message': message,
            'sha': sha,
            'committer': committer,
        }
        if branch is not None:
            data['branch'] = branch
        headers = self.build_headers({'Content-Type': 'application/json'})
        response = yield from aiohttp.request('DELETE', url, data=json.dumps(data), headers=headers)
        return core.ResponseWrapper(response)
