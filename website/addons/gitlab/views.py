"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from dateutil.parser import parse as dateparse
import httplib as http
import logging

from furl import furl
from flask import request, make_response

from framework.exceptions import HTTPError

from modularodm import Q
from modularodm.storage.base import KeyExistsException
from website.oauth.models import ExternalAccount

from website.addons.base import generic_views
from website.addons.gitlab.api import GitLabClient, ref_to_params
from website.addons.gitlab.exceptions import NotFoundError, GitLabError
from website.addons.gitlab.settings import DEFAULT_HOSTS
from website.addons.gitlab.serializer import GitLabSerializer
from website.addons.gitlab.utils import (
    get_refs, check_permissions,
    verify_hook_signature, MESSAGES
)

from website.models import NodeLog
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public, must_be_valid_project,
)
from website.util import rubeus

from framework.auth.decorators import must_be_logged_in
from website.util import api_url_for

logger = logging.getLogger(__name__)

SHORT_NAME = 'gitlab'
FULL_NAME = 'GitLab'

############
# Generics #
############

gitlab_account_list = generic_views.account_list(
    SHORT_NAME,
    GitLabSerializer
)

gitlab_import_auth = generic_views.import_auth(
    SHORT_NAME,
    GitLabSerializer
)

def _get_folders(node_addon, folder_id):
    pass

gitlab_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

gitlab_get_config = generic_views.get_config(
    SHORT_NAME,
    GitLabSerializer
)

gitlab_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

gitlab_root_folder = generic_views.root_folder(
    SHORT_NAME
)

@must_be_logged_in
def gitlab_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    GitLab user settings.
    """

    user_addon = auth.user.get_addon('gitlab')
    user_has_auth = False
    if user_addon:
        user_has_auth = user_addon.has_auth

    return {
        'result': {
            'userHasAuth': user_has_auth,
            'urls': {
                'create': api_url_for('gitlab_add_user_account'),
                'accounts': api_url_for('gitlab_account_list'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http.OK

@must_be_logged_in
def gitlab_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""

    f = furl()
    f.host = request.json.get('host').rstrip('/')
    f.scheme = 'https'
    clientId = request.json.get('clientId')
    clientSecret = request.json.get('clientSecret')

    try:
        account = ExternalAccount(
            provider='gitlab',
            provider_name='GitLab',
            display_name=f.host,       # no username; show host
            oauth_key=f.host,          # hijacked; now host
            oauth_secret=clientSecret,   # hijacked; now clientSecret
            provider_id=clientId,   # hijacked; now clientId
        )
        account.save()
    except KeyExistsException:
        # ... or get the old one
        account = ExternalAccount.find_one(
            Q('provider', 'eq', 'gitlab') &
            Q('provider_id', 'eq', clientId)
        )

    user = auth.user
    if account not in user.external_accounts:
        user.external_accounts.append(account)

    user.get_or_add_addon('gitlab', auth=auth)
    user.save()

    return {}

#################
# Special Cased #
#################

@must_not_be_registration
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission('write')
def gitlab_set_config(auth, **kwargs):
    node_settings = kwargs.get('node_addon', None)
    node = kwargs.get('node', None)
    user_settings = kwargs.get('user_addon', None)

    try:
        if not node:
            node = node_settings.owner
        if not user_settings:
            user_settings = node_settings.user_settings
    except AttributeError:
        raise HTTPError(http.BAD_REQUEST)

    # Parse request
    gitlab_user_name = request.json.get('gitlab_user', '')
    gitlab_repo_name = request.json.get('gitlab_repo', '')
    gitlab_repo_id = request.json.get('gitlab_repo_id', '')

    if not gitlab_user_name or not gitlab_repo_name or not gitlab_repo_id:
        raise HTTPError(http.BAD_REQUEST)

    # Verify that repo exists and that user can access
    connection = GitLabClient(external_account=node_settings.external_account)
    repo = connection.repo(gitlab_repo_id)
    if repo is None:
        if user_settings:
            message = (
                'Cannot access repo. Either the repo does not exist '
                'or your account does not have permission to view it.'
            )
        else:
            message = (
                'Cannot access repo.'
            )
        return {'message': message}, http.BAD_REQUEST

    changed = (
        gitlab_user_name != node_settings.user or
        gitlab_repo_name != node_settings.repo or
        gitlab_repo_id != node_settings.repo_id
    )

    # Update hooks
    if changed:

        # Delete existing hook, if any
        node_settings.delete_hook()

        # Update node settings
        node_settings.user = gitlab_user_name
        node_settings.repo = gitlab_repo_name
        node_settings.repo_id = gitlab_repo_id

        # Log repo select
        node.add_log(
            action='gitlab_repo_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'gitlab': {
                    'user': gitlab_user_name,
                    'repo': gitlab_repo_name,
                    'repo_id': gitlab_repo_id,
                }
            },
            auth=auth,
        )

        # Add new hook
        if node_settings.user and node_settings.repo:
            node_settings.add_hook(save=False)

        node_settings.save()

    return {}

@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_download_starball(node_addon, **kwargs):

    ref = request.args.get('ref', 'master')

    connection = GitLabClient(external_account=node_addon.external_account)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, node_addon.repo_id, ref
    )

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp

#########
# HGrid #
#########

@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_root_folder(*args, **kwargs):
    """View function returning the root container for a GitLab repo. In
    contrast to other add-ons, this is exposed via the API for GitLab to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return gitlab_hgrid_data(node_settings, auth=auth, **data)

def gitlab_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = GitLabClient(external_account=node_settings.external_account)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public or node.is_contributor(auth.user):
        try:
            repo = connection.repo(node_settings.repo_id)
        except NotFoundError:
            logger.error('Could not access GitLab repo')
            return None

    try:
        branch, sha, branches = get_refs(node_settings, branch=kwargs.get('branch'), sha=kwargs.get('sha'), connection=connection)
    except (NotFoundError, GitLabError):
        logger.error('GitLab repo not found')
        return

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = check_permissions(node_settings, auth, connection, branch, sha, repo=repo)
    else:
        ref = None
        can_edit = False

    permissions = {
        'edit': can_edit,
        'view': True,
        'private': node_settings.is_private
    }
    urls = {
        'upload': node_settings.owner.api_url + 'gitlab/file/' + branch,
        'fetch': node_settings.owner.api_url + 'gitlab/hgrid/' + branch,
        'branch': node_settings.owner.api_url + 'gitlab/hgrid/root/' + branch,
        'zip': 'https://{0}/{1}/repository/archive.zip?ref={2}'.format(node_settings.external_account.display_name, repo['path_with_namespace'], branch),
        'repo': 'https://{0}/{1}/tree/{2}'.format(node_settings.external_account.display_name, repo['path_with_namespace'], branch)
    }

    branch_names = [each['name'] for each in branches]
    if not branch_names:
        branch_names = [branch]  # if repo un-init-ed then still add default branch to list of branches

    return [rubeus.build_addon_root(
        node_settings,
        repo['path_with_namespace'],
        urls=urls,
        permissions=permissions,
        branches=branch_names,
        private_key=kwargs.get('view_only', None),
        default_branch=repo['default_branch'],
    )]

#########
# Repos #
#########

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission('write')
def gitlab_create_repo(**kwargs):
    repo_name = request.json.get('name')
    user = request.json.get('user')

    if not repo_name:
        raise HTTPError(http.BAD_REQUEST)

    node_settings = kwargs['node_addon']
    connection = GitLabClient(external_account=node_settings.external_account)

    try:
        repo = connection.create_repo(repo_name, auto_init=True)
    except GitLabError:
        raise HTTPError(http.BAD_REQUEST)

    return {
        'user': user,
        'repo': repo,
    }

def add_hook_log(node, gitlab, action, path, date, committer, include_urls=False,
                 sha=None, save=False):
    """Add log event for commit from webhook payload.

    :param node: Node to add logs to
    :param gitlab: GitLab node settings record
    :param path: Path to file
    :param date: Date of commit
    :param committer: Committer name
    :param include_urls: Include URLs in `params`
    :param sha: SHA of updated file
    :param save: Save changes

    """
    gitlab_data = {
        'user': gitlab.user,
        'repo': gitlab.repo,
    }

    urls = {}

    if include_urls:
        url = node.web_url_for('addon_view_or_download_file', path=path, provider=SHORT_NAME)

        urls = {
            'view': '{0}?ref={1}'.format(url, sha),
            'download': '{0}?action=download&ref={1}'.format(url, sha)
        }

    node.add_log(
        action=action,
        params={
            'project': node.parent_id,
            'node': node._id,
            'path': path,
            'gitlab': gitlab_data,
            'urls': urls,
        },
        auth=None,
        foreign_user=committer,
        log_date=date,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_hook_callback(node_addon, **kwargs):
    """Add logs for commits from outside OSF.

    """
    if request.json is None:
        return {}

    # Fail if hook signature is invalid
    verify_hook_signature(
        node_addon,
        request.data,
        request.headers,
    )

    node = kwargs['node'] or kwargs['project']

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] and commit['message'] in MESSAGES.values():
            continue

        _id = commit['id']
        date = dateparse(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            add_hook_log(
                node, node_addon, 'gitlab_' + NodeLog.FILE_ADDED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('modified', []):
            add_hook_log(
                node, node_addon, 'gitlab_' + NodeLog.FILE_UPDATED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('removed', []):
            add_hook_log(
                node, node_addon, 'gitlab_' + NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
