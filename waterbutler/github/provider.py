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
from waterbutler.github.metadata import GithubFileContentMetadata
from waterbutler.github.metadata import GithubFolderContentMetadata
from waterbutler.github.metadata import GithubFileTreeMetadata
from waterbutler.github.metadata import GithubFolderTreeMetadata


GIT_EMPTY_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


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

        if path.endswith('/'):
            if not branch:
                repo = yield from self._fetch_repo()
                branch = repo['default_branch']

            branch_data = yield from self._fetch_branch(branch)
            old_commit_sha = branch_data['commit']['sha']
            old_commit_tree_sha = branch_data['commit']['commit']['tree']['sha']

            # e.g. 'level1', 'level2', or ''
            tree_paths = provider_path.rstrip('/').split('/')
            trees = [{
                'target': tree_paths[0],
                'tree': [
                    {
                        'path': item['path'],
                        'mode': item['mode'],
                        'type': item['type'],
                        'sha': item['sha'],
                    }
                    for item in (yield from self._fetch_tree(old_commit_tree_sha))['tree']
                ]
            }]
            for idx, tree_path in enumerate(tree_paths[:-1]):
                try:
                    tree_sha = next(x for x in trees[-1]['tree'] if x['path'] == tree_path)['sha']
                except StopIteration:
                    raise exceptions.MetadataError(
                        'Could not delete folder \'{0}\''.format(path),
                        code=404,
                    )
                trees.append({
                    'target': tree_paths[idx + 1],
                    'tree': [
                        {
                            'path': item['path'],
                            'mode': item['mode'],
                            'type': item['type'],
                            'sha': item['sha'],
                        }
                        for item in (yield from self._fetch_tree(tree_sha))['tree']
                    ]
                })

            # The last tree's structure is rewritten w/o the target folder, all others
            # in the hierarchy are simply updated to reflect this change.
            tree = trees.pop()
            if tree['target'] == '':
                # Git Empty SHA
                tree_sha = GIT_EMPTY_SHA
            else:
                # Delete the folder from the tree
                for item in tree['tree']:
                    if item['path'] == tree['target']:
                        tree['tree'].remove(item)
                        break
                tree_data = yield from self._create_tree({'tree': tree['tree']})
                tree_sha = tree_data['sha']
                # Update parent tree(s)
                for tree in reversed(trees):
                    for item in tree['tree']:
                        if item['path'] == tree['target']:
                            item['sha'] = tree_sha
                            break
                    tree_data = yield from self._create_tree({'tree': tree['tree']})
                    tree_sha = tree_data['sha']

            # Create a new commit which references our top most tree change.
            message = message or 'Folder deleted on behalf of WaterButler'
            commit_resp = yield from self.make_request(
                'POST',
                self.build_repo_url('git', 'commits'),
                headers={'Content-Type': 'application/json'},
                data=json.dumps({
                    'message': message,
                    'tree': tree_sha,
                    'parents': [
                        old_commit_sha,
                    ],
                }),
                expects=(201, ),
                throws=exceptions.DeleteError,
            )
            commit_data = yield from commit_resp.json()
            commit_sha = commit_data['sha']

            # Update repository reference, point to the newly created commit.
            ref_resp = yield from self.make_request(
                'PATCH',
                self.build_repo_url('git', 'refs', 'heads', branch),
                headers={'Content-Type': 'application/json'},
                data=json.dumps({
                    'sha': commit_sha,
                }),
                expects=(200, ),
                throws=exceptions.DeleteError,
            )
            yield from ref_resp.json()
        else:
            message = message or 'File deleted on behalf of WaterButler'
            data = {
                'message': message,
                'sha': sha,
                'committer': self.committer,
            }
            if branch:
                data['branch'] = branch
            yield from self.make_request(
                'DELETE',
                self.build_repo_url('contents', provider_path),
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
    def _fetch_repo(self):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url(),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _fetch_branch(self, branch):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('branches', branch)
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _fetch_contents(self, path, ref=None):
        url = furl.furl(self.build_repo_url('contents', path))
        if ref:
            url.args.update({'ref': ref})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _fetch_tree(self, sha, recursive=False):
        url = furl.furl(self.build_repo_url('git', 'trees', sha))
        if recursive:
            url.args.update({'recursive': 1})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _create_tree(self, tree):
        resp = yield from self.make_request(
            'POST',
            self.build_repo_url('git', 'trees'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps(tree),
            expects=(201, ),
            throws=exceptions.DeleteError,
        )
        return (yield from resp.json())

    def _is_sha(self, ref):
        # sha1 is always 40 characters in length
        try:
            if len(ref) != 40:
                return False
            # sha1 is always base 16 (hex)
            int(ref, 16)
        except (TypeError, ValueError, ):
            return False
        return True

    @asyncio.coroutine
    def _metadata_folder(self, path, ref=None, recursive=False, **kwargs):
        provider_path = self.build_path(path)
        parent_path = os.path.dirname(provider_path.rstrip('/'))

        import pdb; pdb.set_trace()

        # if we have a sha or recursive lookup specified we'll need to perform
        # the operation using the git/trees api which requires a sha.
        if self._is_sha(ref) or recursive:
            if self._is_sha(ref):
                tree_sha = ref
            elif parent_path == '':
                if not ref:
                    repo = yield from self._fetch_repo()
                    ref = repo['default_branch']
                branch_data = yield from self._fetch_branch(ref)
                tree_sha = branch_data['commit']['commit']['tree']['sha']
            else:
                data = yield from self._fetch_contents(parent_path, ref=ref)
                try:
                    tree_sha = next(x for x in data if x['path'] == provider_path.rstrip('/'))['sha']
                except StopIteration:
                    raise exceptions.MetadataError(
                        'Could not find folder \'{0}\''.format(path),
                        code=404,
                    )

            data = yield from self._fetch_tree(tree_sha, recursive=recursive)

            ret = []
            for item in data['tree']:
                if item['type'] == 'tree':
                    ret.append(GithubFolderTreeMetadata(item, folder=provider_path).serialized())
                else:
                    ret.append(GithubFileTreeMetadata(item, folder=provider_path).serialized())
            return ret
        else:
            data = yield from self._fetch_contents(provider_path, ref=ref)

            ret = []
            for item in data:
                if item['type'] == 'dir':
                    ret.append(GithubFolderContentMetadata(item).serialized())
                else:
                    ret.append(GithubFileContentMetadata(item).serialized())
            return ret

    @asyncio.coroutine
    def _metadata_file(self, path, ref=None, **kwargs):
        provider_path = self.build_path(path)

        data = yield from self._fetch_contents(provider_path, ref)

        if isinstance(data, list):
            raise exceptions.MetadataError(
                'Could not retrieve file \'{0}\''.format(path),
                code=404,
            )

        return GithubFileContentMetadata(data).serialized()
