# -*- coding: utf-8 -*-

import os
import re
import time
import urllib
import logging
import httplib as http
from slugify import Slugify
from dateutil.parser import parse as parse_date

from framework.exceptions import HTTPError
from framework.auth import get_user
from framework.analytics import get_basic_counters


from website.addons.base import AddonError
from website.profile.utils import reduce_permissions
from website.dates import FILE_MODIFIED

from website.addons.base.utils import NodeLogger

from . import settings as gitlab_settings
from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab.services import hookservice


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


def create_node(node_settings, check_ready=False):
    """Provision GitLab project.

    :param GitlabNodeSettings node_settings: GitLab node model

    """
    # Quit if OSF node is already linked to a Gitlab project
    if node_settings.project_id:
        return

    node = node_settings.owner
    user_settings = node.contributors[0].get_or_add_addon('gitlab')

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

    if check_ready:
        initialized = check_project_initialized(node_settings)
        if not initialized:
            raise AddonError('Project not ready')

    # Add web hook
    hook_service = hookservice.GitlabHookService(node_settings)
    hook_service.create(save=True)
    # node_settings.add_hook(save=True)


def setup_user(user):
    """Ensure user add-on model and provision GitLab user account.

    :param User user: OSF user
    :returns: User add-on model

    """
    user_settings = user.get_or_add_addon('gitlab')
    create_user(user_settings)
    return user_settings


def setup_node(node, check_ready=False):
    """Ensure node add-on model and provision GitLab project.

    :param Node node: OSF node
    :param bool check_ready: Wait until GitLab project is ready
    :returns: Node add-on model

    """
    node_settings = node.get_or_add_addon('gitlab')
    create_node(node_settings, check_ready=check_ready)
    return node_settings


def check_project_initialized(node_settings, tries=20, delay=0.1):
    """Ping the `ready` endpoint until the GitLab project exists.

    :param GitlabNodeSettings node_settings: Node settings object
    :param int tries: Maximum number of tries
    :param float delay: Delay between tries
    :returns: Project ready

    """
    for _ in range(tries):
        try:
            status = client.getprojectready(node_settings.project_id)
            if status['ready']:
                return True
        except GitlabError:
            pass
        logger.info('GitLab project not initialized.')
        time.sleep(delay)
    return False


type_to_kind = {
    'tree': 'folder',
    'blob': 'file',
}


def kwargs_to_path(kwargs, required=True):
    """

    """
    path = kwargs.get('path')
    if path:
        return urllib.unquote_plus(path).rstrip('/')
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
    :returns: Dict of URLs

    """
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
# See https://github.com/gitlabhq/gitlabhq/blob/master/lib/gitlab/regex.rb#L52
# Hack: `Slugify::set_pretranslate` is currently broken and doesn't accept
# callables; until our PR is accepted, set the _pretranslate attribute
# directly.
gitlab_slugify = Slugify(safe_chars='.')
gitlab_slugify._pretranslate = lambda value: re.sub(r'\.git$', '', value)


def get_download_count(node, path, sha=None):
    """Get unique and total download counts for a file by path and optional
    keyword arguments.

    :param Node node: Node object
    :param str path: Path to file
    :param str sha: Commit ID
    :returns: Tuple of (unique, total)

    """
    clean_path = path.replace('.', '_')
    parts = ['download', node._id, clean_path]
    if sha:
        parts.append(sha)
    key = ':'.join(parts)
    return get_basic_counters(key)


def item_to_hgrid(node, item, path, permissions, branch=None, sha=None):
    fullpath = os.path.join(path, item['name'])
    out = {
        'name': item['name'],
        'kind': type_to_kind[item['type']],
        'permissions': permissions,
        'urls': build_full_urls(node, item, fullpath, branch, sha),
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
    :returns: User if email found in OSF, else email address

    """
    return get_user(username=author['email']) or author['name']


def resolve_gitlab_commit_author(commit):
    """Resolve GitLab commit data to name and URL, using OSF user information
    if available.

    :param dict commit: JSON commit data
    :returns: Dict of committer name and URL

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
    :returns: Dict of commit data

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


def ref_or_default(node_settings, data):
    """Get the git reference (SHA or branch) from view arguments; return the
    default reference if none is supplied.

    :param GitlabNodeSettings node_settings: Gitlab node settings
    :param dict data: View arguments
    :returns: SHA or branch if reference found, else None

    """
    return (
        data.get('sha')
        or data.get('branch')
        or get_default_branch(node_settings)
    )


def get_default_file_sha(node_settings, path, branch=None):
    if node_settings.project_id is None:
        raise AddonError('No project ID attached to settings')
    commits = client.listrepositorycommits(
        node_settings.project_id,
        ref_name=branch, path=path,
    )
    return commits[0]['id']


def get_default_branch(node_settings):
    """Get default branch of GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :returns: Name of default branch

    """
    if node_settings.project_id is None:
        raise AddonError('No project ID attached to settings')
    project = client.getproject(node_settings.project_id)
    return project['default_branch']


def get_branch_id(node_settings, branch):
    """Get latest commit SHA for branch of GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :param str branch: Branch name
    :returns: SHA of branch

    """
    branch_json = client.listbranch(node_settings.project_id, branch)
    return branch_json['commit']['id']


def get_default_branch_and_sha(node_settings):
    """Get default branch and SHA for GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :returns: Tuple of (branch, SHA)

    """
    branches_json = client.listbranches(node_settings.project_id)
    if len(branches_json) == 1:
        branch = branches_json[0]['name']
        sha = branches_json[0]['commit']['id']
    else:
        branch = get_default_branch(node_settings)
        branch_json = [
            each
            for each in branches_json
            if each['name'] == branch
        ]
        if not branch_json:
            raise AddonError('Could not find branch')
        sha = branch_json[0]['commit']['id']
    return branch, sha


def get_branch_and_sha(node_settings, data):
    """Get branch and SHA from dictionary of view data.

    :param GitlabNodeSettings node_settings: Node settings
    :param dict data: Dictionary of view data; `branch` and `sha` keys will
        be checked
    :returns: Tuple of (branch, SHA)
    :raises: ValueError if SHA but not branch provided

    """
    branch = data.get('branch')
    sha = data.get('sha')

    # Can't infer branch from SHA
    if sha and not branch:
        raise ValueError('Cannot provide sha without branch')

    if sha is None:
        if branch:
            sha = get_branch_id(node_settings, branch)
        else:
            branch, sha = get_default_branch_and_sha(node_settings)

    branch = branch or get_default_branch(node_settings)

    return branch, sha
