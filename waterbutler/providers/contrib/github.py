# -*- coding: utf-8 -*-

import os
import json
import base64
from asyncio import coroutine

import aiohttp

from waterbutler.providers import core


@core.register_provider('github')
class GithubProvider(core.BaseProvider):

    BASE_URL = 'https://api.github.com/'

    def build_repo_url(self, *segments, **query):
        segments = ('repos', self.identity['owner'], self.identity['repo']) + segments
        return self.build_url(*segments, **query)

    def build_headers(self, extra=None):
        headers = {'Authorization': 'token {}'.format(self.identity['token'])}
        headers.update(extra or {})
        return headers

    @property
    def committer(self):
        return {
            'name': self.auth['name'],
            'email': self.auth['email'],
        }

    @coroutine
    def metadata(self, path, ref=None):
        url = self.build_repo_url('contents', path)
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

    @core.expects(200)
    @coroutine
    def download(self, sha, **kwargs):
        url = self.build_repo_url('git', 'blobs', sha)
        headers = self.build_headers({'Accept': 'application/vnd.github.VERSION.raw'})
        response = yield from aiohttp.request('GET', url, headers=headers)
        return core.ResponseWrapper(response)

    @core.expects(200, 201)
    @coroutine
    def upload(self, obj, path, message, branch=None, **kwargs):
        content = yield from obj.content.read()
        encoded = base64.b64encode(content)
        data = {
            'path': path,
            'message': message,
            'content': encoded.decode('utf-8'),
            'committer': self.committer,
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
        url = self.build_repo_url('contents', path)
        response = yield from aiohttp.request('PUT', url, data=json.dumps(data), headers=self.build_headers())
        return core.ResponseWrapper(response)

    @core.expects(200)
    @coroutine
    def delete(self, path, message, sha, branch=None):
        url = self.build_repo_url('contents', path)
        data = {
            'message': message,
            'sha': sha,
            'committer': self.committer,
        }
        if branch is not None:
            data['branch'] = branch
        headers = self.build_headers({'Content-Type': 'application/json'})
        response = yield from aiohttp.request('DELETE', url, data=json.dumps(data), headers=headers)
        return core.ResponseWrapper(response)
