import os
import json
import base64
import asyncio

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.github import settings
from waterbutler.github.metadata import GithubRevision
from waterbutler.github.metadata import GithubFileMetadata
from waterbutler.github.metadata import GithubFolderMetadata


class GithubProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL

    def build_repo_url(self, *segments, **query):
        segments = ('repos', self.settings['owner'], self.settings['repo']) + segments
        return self.build_url(*segments, **query)

    @property
    def default_headers(self):
        return {'Authorization': 'token {}'.format(self.credentials['token'])}

    @property
    def committer(self):
        return {
            'name': self.auth['name'],
            'email': self.auth['email'],
        }

    @asyncio.coroutine
    def download(self, sha, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'blobs', sha),
            headers={'Accept': 'application/vnd.github.VERSION.raw'},
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(response)

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
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        data = yield from response.json()
        return GithubFileMetadata(data['content']).serialized(), (not existing)

    @asyncio.coroutine
    def delete(self, path, message, sha, branch=None, **kwargs):
        data = {
            'message': message,
            'sha': sha,
            'committer': self.committer,
        }
        if branch is not None:
            data['branch'] = branch
        yield from self.make_request(
            'DELETE',
            self.build_repo_url('contents', path),
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data),
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, ref=None, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('contents', path),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from response.json()

        if isinstance(data, list):
            ret = []
            for item in data:
                if item['type'] == 'folder':
                    ret.append(GithubFolderMetadata(item).serialized())
                else:
                    ret.append(GithubFileMetadata(item).serialized())
            return ret

        return GithubFileMetadata(data).serialized()

    @asyncio.coroutine
    def revisions(self, path, sha=None, **kwargs):
        response = yield from self.make_request(
            'GET',
            self.build_repo_url('commits', path=path, sha=sha),
            expects=(200, ),
            throws=exceptions.RevisionsError
        )

        return [
            GithubRevision(item).serialized()
            for item in (yield from response.json())
        ]
