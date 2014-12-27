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
    def _fetch_branch(self, branch):
        # Get the Branch
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('branches', branch)
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _fetch_path_sha(self, path, commit_sha):
        sha = None
        parent_path = os.path.dirname(path.rstrip('/'))
        if parent_path == '':
            sha = commit_sha
        else:
            resp = yield from self.make_request(
                'GET',
                self.build_repo_url('contents', parent_path, ref=commit_sha),
                expects=(200, ),
                throws=exceptions.MetadataError
            )
            data = yield from resp.json()

            item_path = path.rstrip('/')
            for item in data:
                if item['path'] == item_path:
                    sha = item['sha']
                    break
            if not sha:
                raise Exception('Folder not found...')

        return sha

    @asyncio.coroutine
    def _fetch_tree(self, sha):
        # Get the Current Tree and update
        resp = yield from self.make_request(
            'GET',
            self.build_repo_url('git', 'trees', sha),
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

    @asyncio.coroutine
    def _update_parent_tree(self, path, commit_sha, tree_sha):
        import pdb; pdb.set_trace()

        path_name = os.path.basename(path)
        parent_path = os.path.dirname(path.rstrip('/'))
        parent_tree_sha = yield from self._fetch_path_sha(parent_path, commit_sha)
        parent_tree = yield from self._fetch_tree(parent_tree_sha)

        new_parent_tree = {
            'tree': [
                {
                    'path': item['path'],
                    'mode': item['mode'],
                    'type': item['type'],
                    'sha': tree_sha if item['path'] == path_name else item['sha'],
                }
                for item in parent_tree['tree']
            ]
        }
        data = yield from self._create_tree(new_parent_tree)

        if parent_path:
            return (yield from self._update_parent_tree(
                parent_path,
                commit_sha,
                data['sha']
            ))
        return data['sha']

    @asyncio.coroutine
    def _delete_tree_folder(self, path, tree):
        path_name = os.path.basename(path.rstrip('/'))
        parent_path = os.path.dirname(path.rstrip('/'))
        parent_tree_sha = yield from self._fetch_path_sha(parent_path, commit_sha)
        parent_tree = yield from self._fetch_tree(parent_tree_sha)

        new_parent_tree = {
            'tree': [
                {
                    'path': item['path'],
                    'mode': item['mode'],
                    'type': item['type'],
                    'sha': item['sha'],
                }
                for item in parent_tree['tree']
                if item['path'] != path_name
            ]
        }
        data = yield from self._create_tree(new_parent_tree)

        if parent_path:
            return (yield from self._update_parent_tree(
                parent_path,
                commit_sha,
                data['sha']
            ))
        return data['sha']

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
                    raise Exception('Folder not found...')

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

            # Delete the folder from the tree
            tree = trees.pop()

            if tree['target'] == '':
                # Git empty tree
                tree_sha = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
            else:
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














            import pdb; pdb.set_trace()

            # Create a Commit
            message = message or 'Folder deleted on behalf of WaterButler'
            new_commit = {
                'message': message,
                'tree': tree_sha,
                'parents': [
                    old_commit_sha,
                ],
            }
            commit_resp = yield from self.make_request(
                'POST',
                self.build_repo_url('git', 'commits'),
                headers={'Content-Type': 'application/json'},
                data=json.dumps(new_commit),
                expects=(201, ),
                throws=exceptions.DeleteError,
            )
            commit_data = yield from commit_resp.json()

            # Update Reference to the New Commit
            update_ref = {
                # 'ref': 'refs/heads/{}'.format(branch),
                'sha': commit_data['sha'],
            }
            ref_resp = yield from self.make_request(
                'PATCH',
                self.build_repo_url('git', 'refs', 'heads', branch),
                headers={'Content-Type': 'application/json'},
                data=json.dumps(update_ref),
                expects=(200, ),
                # expects=(201, ),
                throws=exceptions.DeleteError,
            )
            ref_data = yield from ref_resp.json()
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

        i = 0

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

    # @asyncio.coroutine
    # def _get_tree_sha(self, path, ref):
    #     if path == '':
    #         if self._is_sha(ref):
    #             return ref
    #
    #         resp = yield from self.make_request(
    #             'GET',
    #             self.build_repo_url('branches', ref)
    #         )
    #         data = yield from resp.json()
    #         return data['commit']['sha']
    #
    #     resp = yield from self.make_request(
    #         'GET',
    #         self.build_repo_url('contents', os.path.dirname(path.rstrip('/')), ref=ref),
    #         expects=(200, ),
    #         throws=exceptions.MetadataError
    #     )
    #
    #     data = yield from resp.json()
    #
    #     # Find the matching path and return the sha
    #     item_path = path.rstrip('/')
    #     for item in data:
    #         if item['path'] == item_path:
    #             return item['sha']
    #     raise exceptions.MetadataError(
    #         'Could not retrieve folder \'{0}\''.format(path),
    #         code=404,
    #     )

    @asyncio.coroutine
    def _get_tree(self, path, ref, recursive=False):
        # Enumerate the parent's parent folder to find the parent's sha
        parent_path = os.path.dirname(os.path.dirname(path.rstrip('/')))
        sha = None
        if parent_path == '':
            if self._is_sha(ref):
                sha = ref
            else:
                if not ref:
                    repo = yield from self._fetch_repo()
                    ref = repo['default_branch']

                resp = yield from self.make_request(
                    'GET',
                    self.build_repo_url('branches', ref)
                )
                data = yield from resp.json()
                sha = data['commit']['sha']
        else:
            resp = yield from self.make_request(
                'GET',
                self.build_repo_url('contents', parent_path, ref=ref),
                expects=(200, ),
                throws=exceptions.MetadataError
            )
            data = yield from resp.json()
            item_path = os.path.dirname(path)
            for item in data:
                if item['path'] == item_path:
                    sha = item['sha']
                    break
            if not sha:
                raise Exception('Folder not found...')

        url = furl.furl(self.build_repo_url('git', 'trees', sha))
        if recursive:
            url.args.add({'recursive': 1})
        resp = yield from self.make_request(
            'GET',
            url.url,
            expects=(200, ),
            throws=exceptions.MetadataError
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

        if ref is None:
            # get latest SHA of the default branch
            repo = yield from self._fetch_repo()
            ref = repo['default_branch']
        data = yield from self._get_tree(provider_path, ref, recursive=recursive)

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
