import os
import re
import uuid
import urllib
import urlparse
import subprocess
import httplib as http
from slugify import get_slugify

from framework.exceptions import HTTPError

from website.profile.utils import reduce_permissions

import settings as gitlab_settings
from api import client
from exceptions import GitlabError


def initialize_repo(node_settings):
    """

    """
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


def create_user(user_settings):
    """

    """
    # Quit if OSF user is already linked to a Gitlab user
    if user_settings.user_id:
        return

    user = user_settings.owner
    password = str(uuid.uuid4())

    # Create Gitlab user
    status = client.createuser(
        name=user.fullname,
        username=user._id,
        password=password,
        email=user.username,
        projects_limit=gitlab_settings.PROJECTS_LIMIT,
    )

    # Save changes to settings model
    if status:
        user_settings.user_id = status['id']
        user_settings.username = user.fullname
        user_settings.password = password
        user_settings.save()
    else:
        raise GitlabError('Could not create user')


def create_node(node_settings, initialize=True):
    """

    """
    # Quit if OSF node is already linked to a Gitlab project
    if node_settings.project_id:
        return

    node = node_settings.owner
    user_settings = node.creator.get_or_add_addon('gitlab')

    # Create Gitlab project
    response = client.createprojectuser(
        user_settings.user_id, node._id
    )
    if response:
        node_settings.creator_osf_id = node.creator._id
        node_settings.project_id = response['id']
        if initialize:
            initialize_repo(node_settings)
            # Hack: GitLab doesn't seem to allow uploads until after a
            # request of some kind is made.
            client.listrepositorytree(node_settings.project_id)
        node_settings.save()


def setup_user(user):
    """

    """
    user_settings = user.get_or_add_addon('gitlab')
    create_user(user_settings)
    return user_settings


def setup_node(node, initialize=True):
    """

    """
    node_settings = node.get_or_add_addon('gitlab')
    create_node(node_settings, initialize=initialize)
    return node_settings


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


def build_urls(node, item, path, branch=None, sha=None):

    quote_path = urllib.quote_plus(path.encode('utf-8'))
    quote_path = None if not quote_path else quote_path

    if item['type'] == 'tree':
        return {
            'upload': node.api_url_for(
                'gitlab_upload_file',
                path=None, branch=branch
            ),
            'fetch': node.api_url_for(
                'gitlab_list_files',
                path=quote_path, branch=branch, sha=sha
            ),
        }
    elif item['type'] == 'blob':
        return {
            'view': node.web_url_for(
                'gitlab_view_file',
                path=quote_path, branch=branch, sha=sha
            ),
            'download': node.web_url_for(
                'gitlab_download_file',
                path=quote_path, branch=branch, sha=sha
            ),
            'delete': node.api_url_for(
                'gitlab_delete_file',
                path=quote_path, branch=branch
            ),
        }
    raise ValueError('Item must have type "tree" or "blob"')


# Gitlab file names can only contain alphanumeric and [_.-?] and must not end
# with ".git"
# See https://github.com/gitlabhq/gitlabhq/blob/master/lib/gitlab/regex.rb#L52
gitlab_slugify = get_slugify(
    safe_chars='.',
    pretranslate=lambda value: re.sub(r'\.git$', '', value)
)


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
