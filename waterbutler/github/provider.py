import os
import json
import base64
import asyncio

import furl

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.github import settings
from waterbutler.github.metadata import GithubRevision
from waterbutler.github.metadata import GithubFileTreeMetadata
from waterbutler.github.metadata import GithubFolderTreeMetadata
from waterbutler.github.metadata import GithubFileContentMetadata


class GithubProvider(provider.BaseProvider):

    BASE_URL = settings.BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.name = self.auth['name']
        self.email = self.auth['email']
        self.token = self.credentials['token']
        self.owner = self.settings['owner']
        self.repo = self.settings['repo']

    @property
    def default_headers(self):
        return {'Authorization': 'token {}'.format(self.token)}

    @property
    def committer(self):
        return {
            'name': self.name,
            'email': self.email,
        }

    def build_repo_url(self, *segments, **query):
        segments = ('repos', self.owner, self.repo) + segments
        return self.build_url(*segments, **query)

    @asyncio.coroutine
    def download(self, sha, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'blobs', sha),
            headers={'Accept': 'application/vnd.github.VERSION.raw'},
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def upload(self, stream, path, message=None, branch=None, **kwargs):
        content = yield from stream.read()
        encoded = base64.b64encode(content)
        message = message or 'File uploaded on behalf of WaterButler'

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

        resp = yield from self.make_request(
            'PUT',
            self.build_repo_url('contents', path, branch=branch),
            data=json.dumps(data),
            expects=(200, 201),
            throws=exceptions.UploadError,
        )
        data = yield from resp.json()
        return GithubFileContentMetadata(data['content']).serialized(), (not existing)

    @asyncio.coroutine
    def delete(self, path, sha=None, message=None, branch=None, **kwargs):
        provider_path = self.build_path(path)
        if not sha:
            sha = self._get_tree_sha(provider_path, ref=branch)

        message = message or 'File deleted on behalf of WaterButler'
        if path.endswith('/'):
            message = 'Folder deleted on behalf of WaterButler'

        data = {
            'message': message,
            'sha': sha,
            'committer': self.committer,
        }
        if branch:
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
    def metadata(self, path, ref=None, recursive=False, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a file or folder
        :param str ref: A branch or a commit SHA
        :rtype dict:
        :rtype list:
        """
        if not path or path.endswith('/'):
            return (yield from self._metadata_folder(path, ref=ref, recursive=recursive, **kwargs))
        else:
            return (yield from self._metadata_file(path, ref=ref, **kwargs))

    @asyncio.coroutine
    def revisions(self, path, sha=None, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('commits', path=path, sha=sha),
            expects=(200, ),
            throws=exceptions.RevisionsError
        )

        return [
            GithubRevision(item).serialized()
            for item in (yield from resp.json())
        ]

    def build_path(self, path, prefix_slash=False, suffix_slash=True):
        """Validates and converts a WaterButler specific path to a Provider specific path
        :param str path: WaterButler specific path
        :rtype str: Provider specific path
        """
        return super().build_path(path, prefix_slash=prefix_slash, suffix_slash=suffix_slash)

    @asyncio.coroutine
    def _get_repo(self):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url(),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _get_tree_sha(self, path, ref):
        if path == '':
            if self._is_sha(ref):
                return ref

            resp = yield from self.make_request(
                'GET',
                self.build_repo_url('branches', ref)
            )
            data = yield from resp.json()
            return data['commit']['sha']

        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('contents', os.path.dirname(path.rstrip('/')), ref=ref),
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()

        item_path = path.rstrip('/')
        for item in data:
            if item['path'] == item_path:
                return item['sha']
        raise exceptions.MetadataError(
            'Could not retrieve folder \'{0}\''.format(path),
            code=404,
        )

    def _is_sha(self, ref):
        # sha1 is always 40 characters in length
        if len(ref) != 40:
            return False
        try:
            # sha1 is always base 16 (hex)
            int(ref, 16)
        except ValueError:
            return False
        return True

    @asyncio.coroutine
    def _metadata_folder(self, path, ref=None, recursive=False, **kwargs):
        provider_path = self.build_path(path)

        if ref is None:
            # get latest SHA of the default branch
            repo = yield from self._get_repo()
            ref = repo['default_branch']
        sha = yield from self._get_tree_sha(provider_path, ref)

        url = furl.furl(self.build_repo_url('git/trees', sha))
        if recursive:
            url.args.update({'recursive': 1})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()

        if not isinstance(data['tree'], list):
            raise exceptions.MetadataError(
                'Could not retrieve folder \'{0}\''.format(path),
                code=404,
            )

        ret = []
        for item in data['tree']:
            if item['type'] == 'tree':
                ret.append(GithubFolderTreeMetadata(item, folder=provider_path).serialized())
            else:
                ret.append(GithubFileTreeMetadata(item, folder=provider_path).serialized())
        return ret

    @asyncio.coroutine
    def _metadata_file(self, path, ref=None, **kwargs):
        provider_path = self.build_path(path)

        url = furl.furl(self.build_repo_url('contents', provider_path))
        if ref:
            url.args.update({'ref', ref})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()

        if isinstance(data, list):
            raise exceptions.MetadataError(
                'Could not retrieve file \'{0}\''.format(path),
                code=404,
            )

        return GithubFileContentMetadata(data).serialized()
