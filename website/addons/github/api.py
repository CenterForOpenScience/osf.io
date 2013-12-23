"""

"""

import os
import base64
import requests

from hurry.filesize import size, alternative

API_URL = 'https://api.github.com/'

GITHUB_USER = 'jmcarp'
GITHUB_TOKEN = '15bbe00083ffa522f55dc8079c017f795988f92c'

GITHUB_AUTH = (
    GITHUB_USER,
    GITHUB_TOKEN,
)

def get_repo(user, repo):

    req = requests.get(
        os.path.join(API_URL, 'repos', user, repo),
        auth=GITHUB_AUTH,
    )
    if req.status_code == 200:
        return req.json()

def get_branches(user, repo, branch=None):

    url = os.path.join(API_URL, 'repos', user, repo, 'branches')
    if branch:
        url = os.path.join(url, branch)

    req = requests.get(url, auth=GITHUB_AUTH)
    if req.status_code == 200:
        return req.json()

def get_commits(user, repo):

    req = requests.get(
        os.path.join(API_URL, 'repos', user, repo, 'commits'),
        auth=GITHUB_AUTH,
    )
    if req.status_code == 200:
        return req.json()

def get_tree(user, repo, branch=None, sha=None):

    if sha is None:
        if branch:
            commit_id = branch
        else:
            _repo = get_repo(user, repo)
            commit_id = _repo['default_branch']
    else:
        commit_id = sha

    req = requests.get(
        os.path.join(
            API_URL, 'repos', user, repo, 'git', 'trees', commit_id
        ),
        params={'recursive': 1},
        auth=GITHUB_AUTH,
    )

    if req.status_code == 200:
        return commit_id, req.json()
    return commit_id, None

def get_file(user, repo, path):

    req = requests.get(
        os.path.join(
            API_URL, 'repos', user, repo, 'contents', path
        ),
        auth=GITHUB_AUTH,
    )
    if req.status_code == 200:
        data = req.json()
        contents = data['content']
        return data['name'], base64.b64decode(contents)

def get_tarball(user, repo):

    req = requests.get(
        os.path.join(
            API_URL, 'repos', user, repo, 'tarball'
        ),
        auth=GITHUB_AUTH,
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
