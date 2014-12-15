import os
import json
import base64
import asyncio

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions


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

    @core.expects(200, error=exceptions.DownloadError)
    @asyncio.coroutine
    def download(self, sha, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'blobs', sha),
            headers={'Accept': 'application/vnd.github.VERSION.raw'},
        )
        return streams.ResponseStreamReader(response)

    @core.expects(200, 201, error=exceptions.UploadError)
    @asyncio.coroutine
    def upload(self, stream, path, message, branch=None, **kwargs):
        content = yield from stream.read()
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
        return streams.ResponseStreamReader(response)

    @core.expects(200, error=exceptions.DeleteError)
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
        return streams.ResponseStreamReader(response)

    @asyncio.coroutine
    def metadata(self, path, ref=None):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('contents', path),
        )
        data = yield from response.json()
        return [
            GithubMetadata(item).serialized()
            for item in data
        ]


class GithubMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 'github'

    @property
    def kind(self):
        return 'file' if self.raw['type'] == 'file' else 'folder'

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return self.raw['path']

    @property
    def size(self):
        return self.raw['size']

    @property
    def modified(self):
        return None

    @property
    def extra(self):
        return {
            'sha': self.raw['sha']
        }
