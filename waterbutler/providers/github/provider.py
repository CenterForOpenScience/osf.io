import os
import json
import asyncio

import furl

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions
from waterbutler.core.path import WaterButlerPath

from waterbutler.providers.github import settings
from waterbutler.providers.github.metadata import GitHubRevision
from waterbutler.providers.github.metadata import GitHubFileContentMetadata
from waterbutler.providers.github.metadata import GitHubFolderContentMetadata
from waterbutler.providers.github.metadata import GitHubFileTreeMetadata
from waterbutler.providers.github.metadata import GitHubFolderTreeMetadata


GIT_EMPTY_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


class GitHubProvider(provider.BaseProvider):
    NAME = 'github'
    BASE_URL = settings.BASE_URL

    @staticmethod
    def is_sha(ref):
        # sha1 is always 40 characters in length
        try:
            if len(ref) != 40:
                return False
            # sha1 is always base 16 (hex)
            int(ref, 16)
        except (TypeError, ValueError, ):
            return False
        return True

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.name = self.auth.get('name', None)
        self.email = self.auth.get('email', None)
        self.token = self.credentials['token']
        self.owner = self.settings['owner']
        self.repo = self.settings['repo']

    @asyncio.coroutine
    def validate_path(self, path, **kwargs):
        if not getattr(self, '_repo', None):
            self._repo = yield from self._fetch_repo()
            self.default_branch = self._repo['default_branch']

        path = WaterButlerPath(path)
        path.parts[-1]._id = next(
            (kwargs[key] for key in
            ('fileSha', 'ref', 'branch')
            if key in kwargs),
            self.default_branch
        )

        return path

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

    # def can_intra_move(self, other):
    #     return (
    #         type(self) == type(other) and
    #         self.repo == other.repo and
    #         self.owner == other.owner
    #     )

    @asyncio.coroutine
    def download(self, path, ref=None, **kwargs):
        '''Get the stream to the specified file on github
        :param str path: The path to the file on github
        :param str ref: The git 'ref' a branch or commit sha at which to get the file from
        :param str fileSha: The sha of file to be downloaded if specifed path will be ignored
        :param dict kwargs: Ignored
        '''
        file_sha = path.identifier

        if not GitHubProvider.is_sha(file_sha):
            data = yield from self.metadata(path)
            file_sha = data['extra']['fileSha']

        data = yield from self.metadata(path)

        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'blobs', file_sha),
            headers={'Accept': 'application/vnd.github.VERSION.raw'},
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        return streams.ResponseStreamReader(resp, size=data['size'])

    @asyncio.coroutine
    def upload(self, stream, path, message=None, branch=None, **kwargs):
        assert self.name is not None
        assert self.email is not None

        exists = yield from self.exists(path, ref=path.identifier)
        latest_sha = yield from self._get_latest_sha(ref=path.identifier)

        blob = yield from self._create_blob(stream)

        tree = yield from self._create_tree({
            'base_tree': latest_sha,
            'tree': [{
                'path': path.path,
                'mode': '100644',
                'type': 'blob',
                'sha': blob['sha']
            }]
        })

        commit = yield from self._create_commit({
            'tree': tree['sha'],
            'parents': [latest_sha],
            'committer': self.committer,
            'message': message or settings.UPLOAD_FILE_MESSAGE,
        })

        # Doesn't return anything useful
        yield from self._update_ref(commit['sha'])

        # You're hacky
        return GitHubFileTreeMetadata({
            'path': path.path,
            'sha': blob['sha'],
            'size': stream.size,
        }, folder=path.path, commit=commit).serialized(), not exists

    @asyncio.coroutine
    def delete(self, path, sha=None, message=None, branch=None, **kwargs):
        path = GitHubPath(path)

        assert self.name is not None
        assert self.email is not None

        if path.is_dir:
            yield from self._delete_folder(path, message, branch, **kwargs)
        else:
            yield from self._delete_file(path, sha, message, branch, **kwargs)

    @asyncio.coroutine
    def metadata(self, path, ref=None, recursive=False, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a file or folder
        :param str ref: A branch or a commit SHA
        :rtype dict:
        :rtype list:
        """
        if path.is_dir:
            return (yield from self._metadata_folder(path, ref=ref, recursive=recursive, **kwargs))
        else:
            return (yield from self._metadata_file(path, ref=ref, **kwargs))

    @asyncio.coroutine
    def revisions(self, path, sha=None, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('commits', path=path.path, sha=path.identifier),
            expects=(200, ),
            throws=exceptions.RevisionsError
        )

        return [
            GitHubRevision(item).serialized()
            for item in (yield from resp.json())
        ]

    @asyncio.coroutine
    def create_folder(self, path, branch=None, message=None, **kwargs):
        WaterButlerPath.validate_folder(path)

        assert self.name is not None
        assert self.email is not None
        message = message or settings.UPLOAD_FILE_MESSAGE

        keep_path = path.child('.gitkeep')

        data = {
            'path': keep_path,
            'message': message,
            'content': '',
            'committer': self.committer,
        }

        if path.identifier and not GitHubProvider.is_sha(path.identifier):
            data['branch'] = path.identifier

        resp = yield from self.make_request(
            'PUT',
            self.build_repo_url('contents', keep_path.path),
            data=json.dumps(data),
            expects=(201, 422, 409),
            throws=exceptions.CreateFolderError
        )

        data = yield from resp.json()

        if resp.status in (422, 409):
            if resp.status == 409 or data.get('message') == 'Invalid request.\n\n"sha" wasn\'t supplied.':
                raise exceptions.FolderNamingConflict(str(path))
            raise exceptions.CreateFolderError(data, code=resp.status)

        data['content']['name'] = path.name
        data['content']['path'] = data['content']['path'].replace('.gitkeep', '')

        return GitHubFolderContentMetadata(data['content'], commit=data['commit']).serialized()

    @asyncio.coroutine
    def _delete_file(self, path, sha=None, message=None, branch=None, **kwargs):
        if not sha:
            raise exceptions.MetadataError('A sha is required for deleting')

        message = message or settings.DELETE_FILE_MESSAGE
        data = {
            'message': message,
            'sha': sha,
            'committer': self.committer,
        }
        if branch:
            data['branch'] = branch
        yield from self.make_request(
            'DELETE',
            self.build_repo_url('contents', path.path),
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data),
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def _delete_folder(self, path, message=None, branch=None, **kwargs):
        if not branch:
            repo = yield from self._fetch_repo()
            branch = repo['default_branch']

        branch_data = yield from self._fetch_branch(branch)
        old_commit_sha = branch_data['commit']['sha']
        old_commit_tree_sha = branch_data['commit']['commit']['tree']['sha']

        # e.g. 'level1', 'level2', or ''
        tree_paths = path.parts
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
        message = message or settings.DELETE_FOLDER_MESSAGE
        commit_resp = yield from self.make_request(
            'POST',
            self.build_repo_url('git', 'commits'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'message': message,
                'committer': self.committer,
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

    @asyncio.coroutine
    def _fetch_branch(self, branch):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('branches', branch)
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _fetch_contents(self, path, ref=None):
        url = furl.furl(self.build_repo_url('contents', path.path))
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
    def _fetch_repo(self):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url(),
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
            throws=exceptions.ProviderError,
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _create_commit(self, commit):
        resp = yield from self.make_request(
            'POST',
            self.build_repo_url('git', 'commits'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps(commit),
            expects=(201, ),
            throws=exceptions.ProviderError,
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _create_blob(self, stream):
        blob_stream = streams.JSONStream({
            'encoding': 'base64',
            'content': streams.Base64EncodeStream(stream),
        })

        resp = yield from self.make_request(
            'POST',
            self.build_repo_url('git', 'blobs'),
            data=blob_stream,
            headers={
                'Content-Length': blob_stream.size,
                'Content-Type': 'application/json',
            },
            expects=(201, ),
            throws=exceptions.UploadError,
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
    def _metadata_folder(self, path, recursive=False, **kwargs):
        # if we have a sha or recursive lookup specified we'll need to perform
        # the operation using the git/trees api which requires a sha.

        if not (self._is_sha(path.identifier) or recursive):
            data = yield from self._fetch_contents(path, ref=path.identifier)

            ret = []
            for item in data:
                if item['type'] == 'dir':
                    ret.append(GitHubFolderContentMetadata(item).serialized())
                else:
                    ret.append(GitHubFileContentMetadata(item).serialized())
            return ret

        #TODO?
        if self._is_sha(ref):
            tree_sha = ref
        elif path.parent.is_root:
            branch_data = yield from self._fetch_branch(self.identifier)
            tree_sha = branch_data['commit']['commit']['tree']['sha']
        else:
            data = yield from self._fetch_contents(parent_path, ref=ref)
            try:
                tree_sha = next(x for x in data if x['path'] == path.path)['sha']
            except StopIteration:
                raise exceptions.MetadataError(
                    'Could not find folder \'{0}\''.format(path),
                    code=404,
                )

        data = yield from self._fetch_tree(tree_sha, recursive=recursive)

        ret = []
        for item in data['tree']:
            if item['type'] == 'tree':
                ret.append(GitHubFolderTreeMetadata(item, folder=path.path).serialized())
            else:
                ret.append(GitHubFileTreeMetadata(item, folder=path.path).serialized())
        return ret

    @asyncio.coroutine
    def _metadata_file(self, path, ref=None, **kwargs):
        data = yield from self._fetch_contents(path, ref)

        if isinstance(data, list):
            raise exceptions.MetadataError(
                'Could not retrieve file \'{0}\''.format(path),
                code=404,
            )

        return GitHubFileContentMetadata(data).serialized()

    @asyncio.coroutine
    def _get_latest_sha(self, ref='master'):
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'refs', 'heads', ref),
            expects=(200, ),
            throws=exceptions.ProviderError
        )
        data = yield from resp.json()
        return data['object']['sha']

    @asyncio.coroutine
    def _update_ref(self, sha, ref='master'):
        resp = yield from self.make_request(
            'POST',
            self.build_repo_url('git', 'refs', 'heads', ref),
            data=json.dumps({
                'sha': sha
            }),
            expects=(200, ),
            throws=exceptions.ProviderError
        )
        return (yield from resp.json())
