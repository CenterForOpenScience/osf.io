# -*- coding: utf-8 -*-

import os
import json
import base64
import asyncio

from waterbutler.providers import core


@core.register_provider('github')
class GithubProvider(core.BaseProvider):

    BASE_URL = 'https://api.github.com/'

    def build_repo_url(self, *segments, **query):
        segments = ('repos', self.identity['owner'], self.identity['repo']) + segments
        return self.build_url(*segments, **query)

    @property
    def default_headers(self):
        return {'Authorization': 'token {}'.format(self.identity['token'])}

    @property
    def committer(self):
        return {
            'name': self.auth['name'],
            'email': self.auth['email'],
        }

    @asyncio.coroutine
    def metadata(self, path, ref=None):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('contents', path),
        )
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
    @asyncio.coroutine
    def download(self, sha, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'blobs', sha),
            headers={'Accept': 'application/vnd.github.VERSION.raw'},
        )
        return core.ResponseWrapper(response)

    @core.expects(200, 201)
    @asyncio.coroutine
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
        response = yield from self.make_request(
            'PUT',
            self.build_repo_url('contents', path),
            data=json.dumps(data),
        )
        return core.ResponseWrapper(response)

    @core.expects(200)
    @asyncio.coroutine
    def delete(self, path, message, sha, branch=None):
        data = {
            'message': message,
            'sha': sha,
            'committer': self.committer,
        }
        if branch is not None:
            data['branch'] = branch
        response = yield from self.make_request(
            'DELETE',
            self.build_repo_url('contents', path),
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data),
        )
        return core.ResponseWrapper(response)
