"""

"""

import os
import json
import base64
import urllib
import datetime

import requests
from requests_oauthlib import OAuth2Session
from hurry.filesize import size, alternative

from . import settings as github_settings

GH_URL = 'https://github.com/'
API_URL = 'https://api.github.com/'

# TODO: Move to redis / memcached
github_cache = {}


class GitHub(object):

    def __init__(self, access_token=None, token_type=None):

        self.access_token = access_token
        self.token_type = token_type

        if access_token and token_type:
            self.session = OAuth2Session(
                github_settings.CLIENT_ID,
                token={
                    'access_token': access_token,
                    'token_type': token_type,
                }
            )
        else:
            self.session = requests

    @classmethod
    def from_settings(cls, settings):
        if settings:
            return cls(
                access_token=settings.oauth_access_token,
                token_type=settings.oauth_token_type,
            )
        return cls()

    def _send(self, url, method='get', output='json', cache=True, **kwargs):
        """

        """
        func = getattr(self.session, method.lower())

        # Add if-modified-since header if needed
        headers = kwargs.pop('headers', {})
        cache_key = '{0}::{1}::{2}'.format(
            url, method, str(kwargs)
        )
        cache_data = github_cache.get(cache_key)
        if cache and cache_data:
            if 'if-modified-since' not in headers:
                headers['if-modified-since'] = cache_data['date'].strftime('%c')

        # Send request
        req = func(url, headers=headers, **kwargs)

        # Pull from cache if not modified
        if cache and cache_data and req.status_code == 304:
            return cache_data['data']

        # Get return value
        rv = None
        if 200 <= req.status_code < 300:
            if output is None:
                rv = req
            else:
                rv = getattr(req, output)
                if callable(rv):
                    rv = rv()

        # Cache return value if needed
        if cache and rv:
            if req.headers.get('last-modified'):
                github_cache[cache_key] = {
                    'data': rv,
                    'date': datetime.datetime.utcnow(),
                }

        return rv

    def user(self, user=None):
        """Fetch a user or the authenticated user.

        :param user: Optional GitHub user name; will fetch authenticated
            user if omitted
        :return dict: GitHub API response

        """
        url = (
            os.path.join(API_URL, 'users', user)
            if user
            else os.path.join(API_URL, 'user')
        )
        return self._send(url, cache=False)

    def repo(self, user, repo):
        """Get a single Github repo's info.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return: Dict of repo information
            See http://developer.github.com/v3/repos/#get

        """
        return self._send(
            os.path.join(API_URL, 'repos', user, repo)
        )

    def branches(self, user, repo, branch=None):
        """List a repo's branches or get a single branch.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str branch: Branch name if getting a single branch
        :return: List of branch dicts
            http://developer.github.com/v3/repos/#list-branches

        """
        url = os.path.join(API_URL, 'repos', user, repo, 'branches')
        if branch:
            url = os.path.join(url, branch)
        return self._send(url)

    def commits(self, user, repo, path=None, sha=None):
        """Get commits for a repo or file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :param str sha: SHA or branch name
        :return list: List of commit dicts from GitHub; see
            http://developer.github.com/v3/repos/commits/

        """
        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'commits'
            ),
            params={
                'path': path,
                'sha': sha,
            }
        )

    def history(self, user, repo, path, sha=None):
        """Get commit history for a file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :param str sha: SHA or branch name
        :return list: List of dicts summarizing commits

        """
        req = self.commits(user, repo, path=path, sha=sha)

        if req:
            return [
                {
                    'sha': commit['sha'],
                    'name': commit['commit']['author']['name'],
                    'email': commit['commit']['author']['email'],
                    'date': commit['commit']['author']['date'],
                }
                for commit in req
            ]

    def tree(self, user, repo, sha, recursive=True):
        """Get file tree for a repo.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str sha: Branch name or SHA
        :param bool recursive: Walk repo recursively
        :param dict registration_data: Registered commit data
        :returns: tuple: Tuple of commit ID and tree JSON; see
            http://developer.github.com/v3/git/trees/

        """
        # NOTE: GitHub will return the tree recursively as long as the
        # recursive param is included, no matter what its value is
        # Therefore, pass NO params for a NON-recursive tree
        params = {'recursive': 1} if recursive else {}
        req = self._send(os.path.join(
                API_URL, 'repos', user, repo, 'git', 'trees',
                urllib.quote_plus(sha),
            ),
            params=params,
        )

        if req is not None:
            return req
        return None

    def file(self, user, repo, path, ref=None):
        """Get a file within a repo and its contents.

        :returns: A tuple of the form (<filename>, <file_content>, <file_size):

        """
        req = self.contents(user=user, repo=repo, path=path, ref=ref)
        if req:
            content = req['content']
            return req['name'], base64.b64decode(content), req['size']
        return None, None, None

    def contents(self, user, repo, path='', ref=None):
        """Get the contents of a path within a repo.
        http://developer.github.com/v3/repos/contents/#get-contents

        """
        params = {
            'ref': ref,
        }

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            cache=True,
            params=params,
        )
        return req

    def starball(self, user, repo, archive='tar', ref=None):
        """Get link for archive download.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str archive: Archive format [tar|zip]
        :param str ref: Git reference
        :returns: tuple: Tuple of headers and file location

        """
        url_parts = [
            API_URL, 'repos', user, repo, archive + 'ball'
        ]
        if ref:
            url_parts.append(ref)

        req = self._send(
            os.path.join(*url_parts),
            cache=False,
            output=None,
        )

        if req.status_code == 200:
            return dict(req.headers), req.content
        return None, None

    def set_privacy(self, user, repo, private):
        """Set privacy of GitHub repo.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param bool private: Make repo private; see
            http://developer.github.com/v3/repos/#edit

        """
        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo
            ),
            method='patch',
            cache=False,
            data=json.dumps({
                'name': repo,
                'private': private,
            })
        )

        return req

    #########
    # Hooks #
    #########

    def hooks(self, user, repo):
        """List webhooks

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return list: List of commit dicts from GitHub; see
            http://developer.github.com/v3/repos/hooks/#json-http

        """

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks',
            )
        )

    def add_hook(self, user, repo, name, config, events=None, active=True):
        """Create a webhook.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return dict: Hook info from GitHub: see see
            http://developer.github.com/v3/repos/hooks/#json-http

        """
        data = {
            'name': name,
            'config': config,
            'events': events or ['push'],
            'active': active,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks'
            ),
            method='post',
            cache=False,
            data=json.dumps(data),
        )

    def delete_hook(self, user, repo, _id):
        """Delete a webhook.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return requests.models.Response: Response object

        """
        # Note: Must set `output` to `None`; no JSON response from this
        # endpoint
        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks', str(_id),
            ),
            'delete',
            cache=False,
            output=None,
        )

    ########
    # CRUD #
    ########

    def upload_file(self, user, repo, path, message, content, sha=None, branch=None, committer=None, author=None):

        data = {
            'message': message,
            'content': base64.b64encode(content),
            'sha': sha,
            'branch': branch,
            'committer': committer,
            'author': author,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            method='put',
            cache=False,
            data=json.dumps(data),
        )

    def delete_file(self, user, repo, path, message, sha, branch=None, committer=None, author=None):

        data = {
            'message': message,
            'sha': sha,
            'branch': branch,
            'committer': committer,
            'author': author,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            method='delete',
            cache=False,
            data=json.dumps(data),
        )

    ########
    # Auth #
    ########

    def revoke_token(self):

        if self.access_token is None:
            return

        return self._send(
            os.path.join(
                API_URL, 'applications', github_settings.CLIENT_ID,
                'tokens', self.access_token,
            ),
            method='delete',
            cache=False,
            output=None,
            auth=(
                github_settings.CLIENT_ID,
                github_settings.CLIENT_SECRET,
            )
        )


def ref_to_params(branch=None, sha=None):

    params = urllib.urlencode({
        key: value
        for key, value in {
            'branch': branch,
            'sha': sha,
        }.iteritems()
        if value
    })

    if params:
        return '?' + params
    return ''


def _build_github_urls(item, node_url, node_api_url, branch, sha):

    quote_path = urllib.quote_plus(item['path'])
    params = ref_to_params(branch, sha)

    if item['type'] in ['tree', 'dir']:
        return {
            'upload': os.path.join(node_api_url, 'github', 'file', quote_path) + '/' + params,
            'fetch': os.path.join(node_api_url, 'github', 'hgrid', item['path']) + '/',
        }
    elif item['type'] in ['file', 'blob']:
        return {
            'view': os.path.join(node_url, 'github', 'file', quote_path) + '/' + params,
            'download': os.path.join(node_url, 'github', 'file', 'download', quote_path) + '/' + params,
            'delete': os.path.join(node_api_url, 'github', 'file', quote_path) + '/' + ref_to_params(branch, item['sha']),
        }
    raise ValueError


<<<<<<< HEAD
def to_hgrid(data, node_url, node_api_url=None, branch=None, sha=None,
             can_edit=True, parent=None):

    grid = []
    folders = {}

    for datum in data:

=======
def to_hgrid(data, node_url, node_api_url=None, branch=None, sha=None):

    grid = []
    cursor = grid

    ref = ref_to_params(branch, sha)

    for datum in data:

        item = {}

        path = datum['path']
        qpath = urllib.quote(path)

        # Build base URLs
        base_url = os.path.join(node_url, 'github', 'file', qpath) + '/'
        base_api_url = os.path.join(node_api_url, 'github', 'file', qpath) + '/'
        #if ref:
        #    base_url += '?' + ref
        #    base_api_url += '?' + ref

>>>>>>> to_hgrid takes urls (strings) as parameters instead of node settings object
        if datum['type'] in ['file', 'blob']:
            item = {
                'kind': 'item',
                'urls': _build_github_urls(
                    datum, node_url, node_api_url, branch, sha
                )
            }
        elif datum['type'] in ['tree', 'dir']:
            item = {
                'kind': 'folder',
                'children': [],
            }
        else:
            continue

        item.update({
            'addon': 'github',
            'permission': {
                'view': True,
                'edit': can_edit,
            },
            'urls': _build_github_urls(
                datum, node_url, node_api_url, branch, sha
            ),
        })

        head, item['name'] = os.path.split(datum['path'])
        if parent:
            head = head.split(parent)[-1]
        if head:
            folders[head]['children'].append(item)
        else:
            grid.append(item)

        # Update cursor
        if item['kind'] == 'folder':
            key = datum['path']
            if parent:
                key = key.split(parent)[-1]
            folders[key] = item

    return grid
