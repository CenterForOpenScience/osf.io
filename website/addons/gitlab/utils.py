import os
import urllib
import urlparse
import subprocess
import httplib as http

from framework.exceptions import HTTPError

from website.profile.utils import reduce_permissions

import settings as gitlab_settings


def initialize_repo(node_settings):

    node = node_settings.owner
    creator_osf_id = node_settings.creator_osf_id

    parsed = urlparse.urlparse(gitlab_settings.HOST)
    hostname = parsed.hostname

    url = 'http://{root}:{pword}@{host}/{user}/{repo}.git'.format(
        root=gitlab_settings.ROOT_NAME,
        pword=gitlab_settings.ROOT_PASS,
        host=hostname,
        user=creator_osf_id,
        repo=node._id,
    )

    # Clone empty repo to temp
    subprocess.check_call(
        ['git', 'clone', url],
        cwd=gitlab_settings.TMP_DIR
    )
    clone_dir = os.path.join(gitlab_settings.TMP_DIR, node._id)

    # Add empty commit
    subprocess.check_call(
        ['git', 'commit', '--allow-empty', '-m', 'initialize'],
        cwd=clone_dir
    )

    # Push to Gitlab
    subprocess.check_call(
        ['git', 'push', 'origin', 'master'],
        cwd=clone_dir
    )


def translate_permissions(permissions):
    osf_permissions = reduce_permissions(permissions)
    return gitlab_settings.ACCESS_LEVELS[osf_permissions]


type_to_kind = {
    'tree': 'folder',
    'blob': 'file',
}


def kwargs_to_path(kwargs, required=True):
    path = kwargs.get('path')
    if path:
        return urllib.unquote_plus(path)
    elif required:
        raise HTTPError(http.BAD_REQUEST)
    return ''


def refs_to_params(branch=None, sha=None):
    refs = {}
    if branch:
        refs['branch'] = branch
    if sha:
        refs['sha'] = sha
    if refs:
        return '?' + urllib.urlencode(refs)
    return ''


def join_truthy(*args):
    return os.path.join(*[arg for arg in args if arg])


def build_urls(node, item, path, branch=None, sha=None):

    quote_path = urllib.quote_plus(path)
    params = refs_to_params(branch, sha)

    files_url = join_truthy(node.url, 'gitlab', 'files', quote_path)
    files_api_url = join_truthy(node.api_url, 'gitlab', 'files', quote_path)
    hgrid_url = join_truthy(node.api_url, 'gitlab', 'grid', quote_path)

    if item['type'] == 'tree':
        return {
            'upload': os.path.join(files_api_url) + '/' + params,
            'fetch': os.path.join(hgrid_url) + '/',
        }
    elif item['type'] == 'blob':
        return {
            'view': os.path.join(files_url) + '/' + params,
            'download': os.path.join(files_url, 'download') + '/' + params,
            'delete': os.path.join(files_api_url) + '/' + refs_to_params(branch)
        }
    raise ValueError('Item must have type "tree" or "blob"')


def item_to_hgrid(node, item, path, permissions, branch=None, sha=None):
    fullpath = os.path.join(path, item['name'])
    return {
        'name': item['name'],
        'kind': type_to_kind[item['type']],
        'permissions': permissions,
        'urls': build_urls(node, item, fullpath, branch, sha),
    }


def gitlab_to_hgrid(node, data, path, permissions, branch=None, sha=None):

    return [
        item_to_hgrid(node, item, path, permissions, branch, sha)
        for item in data
    ]
