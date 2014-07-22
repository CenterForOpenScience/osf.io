# -*- coding: utf-8 -*-

import os
import re
import time
import urllib
import logging
import unicodedata
import httplib as http
from unidecode import unidecode
from mako.template import Template
from dateutil.parser import parse as parse_date

from framework.exceptions import HTTPError
from framework.auth import get_user
from framework.analytics import get_basic_counters

from website import settings
from website.addons.base import AddonError
from website.addons.base.utils import NodeLogger
from website.profile.utils import reduce_permissions
from website.dates import FILE_MODIFIED

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.services import (
    userservice, projectservice, hookservice
)


logger = logging.getLogger(__name__)


def translate_permissions(permissions):
    osf_permissions = reduce_permissions(permissions)
    return gitlab_settings.ACCESS_LEVELS[osf_permissions]


class GitlabNodeLogger(NodeLogger):

    NAME = 'gitlab'

    def __init__(self, node, auth, foreign_user=None, file_obj=None, path=None, date=None,
                 branch=None, sha=None):
        super(GitlabNodeLogger, self).__init__(
            node, auth, foreign_user, file_obj, path, date
        )
        self.branch = branch
        self.sha = sha

    def build_params(self):
        params = super(GitlabNodeLogger, self).build_params()
        params['path'] = self.path
        if self.file_obj or self.path:
            path = self.file_obj.path if self.file_obj else self.path
            params['urls'] = build_full_urls(
                self.node,
                {'type': 'blob'},
                path,
                sha=self.sha,
            )
        params['gitlab'] = {
            'branch': self.branch,
            'sha': self.sha,
        }
        return params


def create_user(user_settings):
    """Provision GitLab user account.

    :param GitlabUserSettings user_settings: GitLab user model

    """
    # Quit if OSF user is already linked to a Gitlab user
    if user_settings.user_id:
        return

    user = user_settings.owner

    # Create Gitlab user
    user_service = userservice.GitlabUserService(user_settings)
    try:
        user_service.create()
    except userservice.UserServiceError:
        raise AddonError(
            'Could not create GitLab user on {0}'.format(
                user._id,
            )
        )


def create_node(node_settings, check_ready=False):
    """Provision GitLab project.

    :param GitlabNodeSettings node_settings: GitLab node l

    """
    # Quit if OSF node is already linked to a Gitlab project
    if node_settings.project_id:
        return

    node = node_settings.owner
    user_settings = node.contributors[0].get_or_add_addon('gitlab')

    project_service = projectservice.GitlabProjectService(node_settings)

    # Create Gitlab project
    try:
        project_service.create(user_settings, node._id)
    except projectservice.ProjectServiceError:
        raise AddonError('Could not create project')

    if check_ready:
        initialized = check_project_initialized(node_settings)
        if not initialized:
            raise AddonError('Project not ready')

    # Add web hook
    hook_service = hookservice.GitlabHookService(node_settings)
    hook_service.create(save=True)


def setup_user(user):
    """Ensure user add-on model and provision GitLab user account.

    :param User user: OSF user
    :return: User add-on model

    """
    user_settings = user.get_or_add_addon('gitlab')
    create_user(user_settings)
    return user_settings


def setup_node(node, check_ready=False):
    """Ensure node add-on model and provision GitLab project.

    :param Node node: OSF node
    :param bool check_ready: Wait until GitLab project is ready
    :return: Node add-on model

    """
    node_settings = node.get_or_add_addon('gitlab')
    create_node(node_settings, check_ready=check_ready)
    return node_settings


def check_project_initialized(node_settings, tries=20, delay=0.1):
    """Ping the `ready` endpoint until the GitLab project exists.

    :param GitlabNodeSettings node_settings: Node settings object
    :param int tries: Maximum number of tries
    :param float delay: Delay between tries
    :return: Project ready

    """
    project_service = projectservice.GitlabProjectService(node_settings)
    for _ in range(tries):
        ready = project_service.ready()
        if ready:
            return True
        logger.info('GitLab project not initialized.')
        time.sleep(delay)
    return False


type_to_kind = {
    'tree': 'folder',
    'blob': 'file',
}


def kwargs_to_path(kwargs, required=True):
    """Extract git path from kwargs.

    :param dict kwargs: Keyword arguments from request
    :param bool required: Path is required
    :raise: `HTTPError` if path is both required and missing

    """
    path = kwargs.get('path')
    if path:
        unquoted = urllib.unquote_plus(path).rstrip('/')
        # Note: GitLab expects unicode in paths to be in decomposed form.
        normalized = unicodedata.normalize('NFKD', unquoted)
        return normalized
    elif required:
        raise HTTPError(http.BAD_REQUEST)
    return ''


def refs_to_params(branch=None, sha=None):
    """

    """
    refs = {}
    if branch:
        refs['branch'] = branch
    if sha:
        refs['sha'] = sha
    if refs:
        return '?' + urllib.urlencode(refs)
    return ''


def build_full_urls(node, item, path, branch=None, sha=None):
    """Build full URLs (i.e., without GUIDs) for a file or folder.

    :param Node node: OSF node
    :param dict item: Dict of GitLab file or folder info
    :param str path: Path to file or folder
    :param str branch: Optional branch name
    :param str sha: Optional commit SHA
    :return: Dict of URLs

    """
    quote_path = path.encode('utf-8')
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
            'root': node.api_url_for('gitlab_hgrid_root_public'),
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
            'render': node.api_url_for(
                'gitlab_get_rendered_file',
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
forbidden_chars_regex = re.compile(r'[^a-z0-9?._-]', flags=re.I)
dot_git_regex = re.compile(r'\.git$', flags=re.I)


def gitlab_slugify(value, repl='_'):
    """Strip forbidden characters from filename. If result is empty or
    comprised entirely of replacement characters, return missing file string.

    :param str value: String to slugify
    :param str repl: Replacement character
    :return: Slugified string or missing file value if empty

    """
    value = unidecode(value)
    value = forbidden_chars_regex.sub(repl, value)
    value = dot_git_regex.sub('', value)
    if not value or not value.replace(repl, ''):
        value = gitlab_settings.MISSING_FILE_NAME
    return value


def get_download_count(node, path, sha=None):
    """Get unique and total download counts for a file by path and optional
    keyword arguments.

    :param Node node: Node object
    :param str path: Path to file
    :param str sha: Commit ID
    :return: Tuple of (unique, total)

    """
    clean_path = path.replace('.', '_')
    parts = ['download', node._id, clean_path]
    if sha:
        parts.append(sha)
    key = ':'.join(parts)
    return get_basic_counters(key)


def item_to_hgrid(node, item, path, permissions, branch=None, sha=None,
                  action_taken=None):
    fullpath = os.path.join(path, item['name'])
    out = {
        'name': item['name'],
        'kind': type_to_kind[item['type']],
        'permissions': permissions,
        'urls': build_full_urls(node, item, fullpath, branch, sha),
        'actionTaken': action_taken,
    }
    if item['type'] == 'blob':
        unique, total = get_download_count(node, fullpath)
        out['downloads'] = total or 0
    return out


def gitlab_to_hgrid(node, data, path, permissions, branch=None, sha=None):

    return [
        item_to_hgrid(node, item, path, permissions, branch, sha)
        for item in data
    ]


def resolve_gitlab_hook_author(author):
    """Resolve GitLab author information to OSF user.

    :param dict author: Author dictionary from GitLab
    :return: User if email found in OSF, else email address

    """
    return get_user(username=author['email']) or author['name']


def resolve_gitlab_commit_author(commit):
    """Resolve GitLab commit data to name and URL, using OSF user information
    if available.

    :param dict commit: JSON commit data
    :return: Dict of committer name and URL

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


def build_guid_urls(guid, branch=None, sha=None):
    params = refs_to_params(branch=branch, sha=sha)
    return {
        'view': '/{0}/'.format(guid._id) + params,
        'download': '/{0}/download/'.format(guid._id) + params,
    }


def serialize_commit(node, path, commit, guid, branch):
    """Serialize GitLab commit to dictionary.

    :param Node node: Parent node
    :param str path: Path to file
    :param dict commit: GitLab commit data
    :param str guid: File GUID
    :param str branch: Branch name
    :return: Dict of commit data

    """
    committer = resolve_gitlab_commit_author(commit)
    unique, total = get_download_count(node, path, sha=commit['id'])
    return {
        'sha': commit['id'],
        'date': parse_date(commit['created_at']).strftime(FILE_MODIFIED),
        'committer': committer,
        'downloads': total or 0,
        'urls': build_guid_urls(guid, branch=branch, sha=commit['id'])
    }


template_path = os.path.join(
    settings.BASE_PATH, 'addons', 'gitlab', 'templates', 'branch_picker.mako'
)
branch_picker_template = Template(open(template_path).read())


def render_branch_picker(branch, sha, branches):
    return branch_picker_template.render(**locals())
