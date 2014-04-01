import os
import re
import urllib
import httplib as http
from slugify import get_slugify
from dateutil.parser import parse as parse_date

from framework.exceptions import HTTPError
from framework.auth import get_user

from website.addons.base import AddonError
from website.profile.utils import reduce_permissions
from website.dates import FILE_MODIFIED

import settings as gitlab_settings
from website.addons.gitlab.api import client, GitlabError


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

    # Create Gitlab user
    try:
        status = client.createuser(
            name=user.fullname,
            username=user._id,
            password=None,
            email=user.username,
            encrypted_password=user.password,
            skip_confirmation=True,
            projects_limit=gitlab_settings.PROJECTS_LIMIT,
        )
    except GitlabError:
        raise AddonError('Could not create GitLab user')

    # Save changes to settings model
    user_settings.user_id = status['id']
    user_settings.username = status['username']
    user_settings.save()


def create_node(node_settings):
    """

    """
    # Quit if OSF node is already linked to a Gitlab project
    if node_settings.project_id:
        return

    node = node_settings.owner
    user_settings = node.creator.get_or_add_addon('gitlab')

    # Create Gitlab project
    try:
        status = client.createprojectuser(
            user_settings.user_id, node._id
        )
        node_settings.creator_osf_id = node.creator._id
        node_settings.project_id = status['id']
        node_settings.save()
    except GitlabError:
        raise AddonError('Could not create project')

    # Add web hook
    node_settings.add_hook(save=True)


def setup_user(user):
    """

    """
    user_settings = user.get_or_add_addon('gitlab')
    create_user(user_settings)
    return user_settings


def setup_node(node):
    """

    """
    node_settings = node.get_or_add_addon('gitlab')
    create_node(node_settings)
    return node_settings


type_to_kind = {
    'tree': 'folder',
    'blob': 'file',
}


def kwargs_to_path(kwargs, required=True):
    path = kwargs.get('path')
    if path:
        return urllib.unquote_plus(path).rstrip('/')
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
                path=quote_path, branch=branch
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


def resolve_gitlab_hook_author(author):
    """Resolve GitLab author information to OSF user.

    :param dict author: Author dictionary from GitLab
    :returns: User if email found in OSF else email address

    """
    return get_user(username=author['email']) or author['name']


def resolve_gitlab_commit_author(commit):
    """Resolve GitLab commit data to name and URL, using OSF user information
    if available.

    :param dict commit: JSON commit data
    :returns: Dictionary of committer name and URL

    """
    committer_user = get_user(username=commit['author_email'])
    if committer_user:
        committer_name = committer_user.fullname
        committer_url = committer_user.url
    else:
        committer_name = commit['author_name']
        committer_url = 'mailto:{0}'.format(commit['author_email'])

    return {
        'name': committer_name,
        'url': committer_url,
    }


def serialize_commit(commit, guid, branch):
    """

    """
    committer = resolve_gitlab_commit_author(commit)
    params = refs_to_params(branch=branch, sha=commit['id'])
    return {
        'sha': commit['id'],
        'date': parse_date(commit['created_at']).strftime(FILE_MODIFIED),
        'committer': committer,
        'urls': {
            'view': '/' + guid._id + '/' + params,
            'download': '/' + guid._id + '/download/' + params,
        },
    }


def ref_or_default(node_settings, data):
    """Get the git reference (SHA or branch) from view arguments; return the
    default reference if none is supplied.

    :param AddonGitlabNodeSettings node_settings: Gitlab node settings
    :param dict data: View arguments
    :returns: SHA or branch if reference found, else None

    """
    ref = data.get('sha') or data.get('branch')
    if ref:
        ret = ref
    elif node_settings.project_id:
        project = client.getproject(node_settings.project_id)
        ret = project['default_branch']
    else:
        raise AddonError('Could not get git ref')
    return ret or gitlab_settings.DEFAULT_BRANCH
