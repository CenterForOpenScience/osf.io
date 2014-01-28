"""

"""

import os
import json
import base64

from requests_oauthlib import OAuth1Session
from hurry.filesize import size, alternative

API_V1_URL = 'https://bitbucket.org/api/1.0/'
API_V2_URL = 'https://bitbucket.org/api/2.0/'


class Bitbucket(object):

    def __init__(self, client_token, client_secret, owner_token, owner_secret):

        self.client_token = client_token
        self.client_secret = client_secret
        self.owner_token = owner_token
        self.owner_secret = owner_secret

        self.session = OAuth1Session(
            client_token,
            client_secret=client_secret,
            resource_owner_key=owner_token,
            resource_owner_secret=owner_secret,
        )

    @classmethod
    def from_settings(cls, settings):
        return cls(
            None, None,
            key=settings.oauth_access_token,
        )

    def _send(self, url, method='get', output='json', **kwargs):
        """

        """
        #
        func = getattr(self.session, method.lower())

        # Send request
        req = func(url, **kwargs)

        # Get return value
        if 200 <= req.status_code < 300:
            if output is None:
                return req
            rv = getattr(req, output)
            if callable(rv):
                return rv()
            return rv

    def tree(self, user, repo, ref, path=None):

        url_parts = [
            API_V1_URL, 'repositories', user, repo, 'src', ref
        ]
        if path is not None:
            url_parts.append(path)

        req = self._send(
            os.path.join(*url_parts)
        )

        # Expand directories
        for directory in req.get('directories', []):
            pass

    def repo(self, user, repo):

        return self._send(
            os.path.join(API_URL, 'repos', user, repo)
        )

    def branches(self, user, repo, branch=None):

        url = os.path.join(API_URL, 'repos', user, repo, 'branches')
        if branch:
            url = os.path.join(url, branch)

        return self._send(url)

    def commits(self, user, repo, path=None):
        """Get commits for a repo or file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :return list: List of commit dicts from GitHub; see
            http://developer.github.com/v3/repos/commits/

        """
        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'commits'
            ),
            params={
                'path': path,
            }
        )

    def history(self, user, repo, path):
        """Get commit history for a file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :return list: List of dicts summarizing commits

        """
        req = self.commits(user, repo, path)

        if req:
            return [
                {
                    'sha': commit['sha'],
                    'name': commit['author']['name'],
                    'email': commit['author']['email'],
                    'date': commit['author']['date'],
                }
                for commit in req
            ]

    def file(self, user, repo, path, ref=None):

        params = {
            'ref': ref,
        }

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            cache=False,
            params=params,
        )

        if req:
            content = req['content']
            return req['name'], base64.b64decode(content)

        return None, None

    def starball(self, user, repo, archive='tar'):

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, archive + 'ball'
            ),
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

#

type_map = {
    'tree': 'folder',
    'blob': 'file',
}

def tree_to_hgrid(tree, user, repo, node, ref=None, hotlink=True):
    """Convert GitHub tree data to HGrid format.

    :param list tree: JSON description of git tree
    :param str user: GitHub user name
    :param str repo: GitHub repo name
    :param Node node: OSF Node
    :param str ref: Branch or SHA
    :param bool hotlink: Hotlink files if ref provided; will yield broken
        links if repo is private

    """
    grid = []

    parent = {
        'uid': 'tree:__repo__',
        'name': 'GitHub :: {0}'.format(repo),
        'parent_uid': 'null',
        'url': '',
        'type': 'folder',
        'uploadUrl': node.api_url + 'github/file/'
    }

    grid.append(parent)

    for item in tree:

        split = os.path.split(item['path'])

        row = {
            'uid': item['type'] + ':' + '||'.join(['__repo__', item['path']]),
            'name': split[1],
            'parent_uid': 'tree:' + '||'.join(['__repo__', split[0]]).strip('||'),
            'type': type_map[item['type']],
            'uploadUrl': node.api_url + 'github/file/',
        }
        if ref is not None:
             row['uploadUrl'] += '?ref=' + ref

        if item['type'] == 'blob':
            row['sha'] = item['sha']
            row['url'] = item['url']
            row['size'] = [
                item['size'],
                size(item['size'], system=alternative)
            ]
            if hotlink and ref:
                row['download'] = os.path.join(
                    GH_URL, user, repo, 'blob', ref, item['path']
                ) + '?raw=true'
            else:
                row['download'] = node.api_url + 'github/file/{0}'.format(item['path'])
                if ref is not None:
                    row['download'] += '?ref=' + ref
                    row['ref'] = ref
        else:
            row['uploadUrl'] = node.api_url + 'github/file/{0}/'.format(item['path'])
            if ref is not None:
                 row['uploadUrl'] += '?ref=' + ref

        grid.append(row)

    return grid
