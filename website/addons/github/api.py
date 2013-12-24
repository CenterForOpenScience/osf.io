"""

"""

import os
import uuid
import base64
import urllib
import datetime
import requests

from hurry.filesize import size, alternative

from website import settings

API_URL = 'https://api.github.com/'
OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'

GITHUB_USER = 'pfftwhat'
GITHUB_TOKEN = '150fbf1af333e58cd9ae22a21dddafb454b95e8d'

CLIENT_ID = '01344fe22202e7f924bc'
CLIENT_SECRET = 'bc8b79abe67ac0c282d4d86dd54515ee5b1a4e27'
SCOPE = ['repo']

GITHUB_AUTH = (
    GITHUB_USER,
    GITHUB_TOKEN,
)

github_cache = {}

def oauth_start_url(node, state=None):
    """

    """
    state = state or str(uuid.uuid4())

    redirect_uri = os.path.join(
        settings.DOMAIN, 'api', 'v1', 'addons', 'github', 'callback', node._id
    )
    query_string = urllib.urlencode({
        'client_id': CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': ','.join(SCOPE),
        'state': state,
    })
    url = '{0}/?{1}'.format(
        OAUTH_AUTHORIZE_URL,
        query_string
    )

    return state, url


def oauth_get_token(code):
    """

    """
    return requests.get(
        OAUTH_ACCESS_TOKEN_URL,
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
        }
    )


class GitHub(object):

    def __init__(self, user=None, token=None, key=None):
        self.user = user
        self.token = token
        self.key = key

    @classmethod
    def from_settings(cls, settings):
        return cls(
            GITHUB_USER, GITHUB_TOKEN,
            key=settings.oauth_access_token,
        )

    def _send(self, url, method='get', output='json', cache=True, **kwargs):
        """

        """
        func = getattr(requests, method)

        # Add access token to params
        params = kwargs.pop('params', {})
        if self.key is not None and 'access_token' not in params:
            params['access_token'] = self.key

        # Build auth
        auth = kwargs.pop('auth', None)
        if 'access_token' not in params:
            if auth is None and self.user is not None and self.token is not None:
                auth = (self.user, self.token)
        else:
            auth = None

        # Add if-modified-since header if needed
        headers = kwargs.pop('headers', {})
        cache_key = '{0}::{1}'.format(url, method)
        cache_data = github_cache.get(cache_key)
        if cache and cache_data:
            if 'if-modified-since' not in headers:
                headers['if-modified-since'] = datetime.datetime.utcnow().strftime('%c')

        # Send request
        req = func(url, params=params, auth=auth, headers=headers, **kwargs)

        # Pull from cache if not modified
        if cache and cache_data and req.status_code == 304:
            return cache_data

        # Get return value
        rv = None
        if req.status_code == 200:
            if output is None:
                rv = req
            else:
                rv = getattr(req, output)
                if callable(rv):
                    rv = rv()

        # Cache return value if needed
        if cache and rv:
            if req.headers.get('last-modified'):
                github_cache[cache_key] = rv

        return rv

    def repo(self, user, repo):

        return self._send(
            os.path.join(API_URL, 'repos', user, repo)
        )

    def branches(self, user, repo, branch=None):

        url = os.path.join(API_URL, 'repos', user, repo, 'branches')
        if branch:
            url = os.path.join(url, branch)

        return self._send(url)

    def commits(self, user, repo):

        return self._send(
            os.path.join(API_URL, 'repos', user, repo, 'commits'),
        )

    def tree(self, user, repo, branch=None, registration_data=None):

        if branch:
            commit_id = branch
        else:
            _repo = self.repo(user, repo)
            if _repo is None:
                return None, None
            commit_id = _repo['default_branch']

        if registration_data is not None:
            for registered_branch in registration_data:
                if commit_id == registered_branch['name']:
                    commit_id = registered_branch['commit']['sha']
                    break

        req = self._send(os.path.join(
                API_URL, 'repos', user, repo, 'git', 'trees', commit_id
            ),
            params={'recursive': 1},
        )

        if req is not None:
            return commit_id, req
        return commit_id, None

    def file(self, user, repo, path):

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            cache=False
        )
        if req:
            content = req['content']
            return req['name'], base64.b64decode(content)

    def tarball(self, user, repo):

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'tarball'
            ),
            cache=False, output=None,
        )

        if req.status_code == 200:
            return dict(req.headers), req.content
        return None, None

#

type_map = {
    'tree': 'folder',
    'blob': 'file',
}

def tree_to_hgrid(tree, repo, node):
    """

    """
    grid = []

    parent = {
        'uid': '__repo__',
        'name': 'GitHub :: {0}'.format(repo),
        'parent_uid': 'null',
        'url': '',
        'type': 'folder',
    }

    grid.append(parent)

    for item in tree:

        split = os.path.split(item['path'])

        row = {
            'uid': item['path'],
            'name': split[1],
            'parent_uid': split[0] if split[0] else '__repo__',
            'url': item['url'],
            'type': type_map[item['type']],
        }

        if item['type'] == 'blob':
            row['size'] = [
                item['size'],
                size(item['size'], system=alternative)
            ]
            row['download'] = node.api_url + 'github/file/{0}'.format(item['path'])

        grid.append(row)

    return grid
