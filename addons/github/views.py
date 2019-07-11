"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from dateutil.parser import parse as dateparse
from rest_framework import status as http_status
import logging

from flask import request, make_response

from framework.exceptions import HTTPError

from addons.base import generic_views
from addons.github.api import GitHubClient
from addons.github.apps import github_hgrid_data
from addons.github.exceptions import GitHubError
from addons.github.serializer import GitHubSerializer
from addons.github.utils import verify_hook_signature, MESSAGES

from osf.models import NodeLog
from osf.utils.permissions import WRITE
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public, must_be_valid_project,
)

logger = logging.getLogger(__name__)

logging.getLogger('github3').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)

SHORT_NAME = 'github'
FULL_NAME = 'GitHub'

############
# Generics #
############

github_account_list = generic_views.account_list(
    SHORT_NAME,
    GitHubSerializer
)

github_import_auth = generic_views.import_auth(
    SHORT_NAME,
    GitHubSerializer
)

github_get_config = generic_views.get_config(
    SHORT_NAME,
    GitHubSerializer
)

github_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

#################
# Special Cased #
#################

@must_not_be_registration
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission(WRITE)
def github_set_config(auth, **kwargs):
    node_settings = kwargs.get('node_addon', None)
    node = kwargs.get('node', None)
    user_settings = kwargs.get('user_addon', None)

    try:
        if not node:
            node = node_settings.owner
        if not user_settings:
            user_settings = node_settings.user_settings
    except AttributeError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Parse request
    github_user_name = request.json.get('github_user', '')
    github_repo_name = request.json.get('github_repo', '')

    if not github_user_name or not github_repo_name:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Verify that repo exists and that user can access
    connection = GitHubClient(external_account=node_settings.external_account)
    repo = connection.repo(github_user_name, github_repo_name)
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
        return {'message': message}, http_status.HTTP_400_BAD_REQUEST

    changed = (
        github_user_name != node_settings.user or
        github_repo_name != node_settings.repo
    )

    # Update hooks
    if changed:

        # Delete existing hook, if any
        node_settings.delete_hook()

        # Update node settings
        node_settings.user = github_user_name
        node_settings.repo = github_repo_name

        # Log repo select
        node.add_log(
            action='github_repo_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'github': {
                    'user': github_user_name,
                    'repo': github_repo_name,
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
@must_have_addon('github', 'node')
def github_download_starball(node_addon, **kwargs):

    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('sha', 'master')

    connection = GitHubClient(external_account=node_addon.external_account)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, archive, ref
    )

    resp = make_response(data)
    for key, value in headers.items():
        resp.headers[key] = value

    return resp

#########
# HGrid #
#########

@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_root_folder(*args, **kwargs):
    """View function returning the root container for a GitHub repo. In
    contrast to other add-ons, this is exposed via the API for GitHub to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return github_hgrid_data(node_settings, auth=auth, **data)

#########
# Repos #
#########

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def github_folder_list(node_addon, **kwargs):
    """ Returns all repos for user.
    """

    return node_addon.get_folders()

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission(WRITE)
def github_create_repo(**kwargs):
    repo_name = request.json.get('name')
    if not repo_name:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    node_settings = kwargs['node_addon']
    connection = GitHubClient(external_account=node_settings.external_account)

    try:
        repo = connection.create_repo(repo_name, auto_init=True)
    except GitHubError:
        # TODO: Check status code
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    return {
        'user': repo.owner.login,
        'repo': repo.name,
    }

#########
# Hooks #
#########

# TODO: Refactor using NodeLogger
def add_hook_log(node, github, action, path, date, committer, include_urls=False,
                 sha=None, save=False):
    """Add log event for commit from webhook payload.

    :param node: Node to add logs to
    :param github: GitHub node settings record
    :param path: Path to file
    :param date: Date of commit
    :param committer: Committer name
    :param include_urls: Include URLs in `params`
    :param sha: SHA of updated file
    :param save: Save changes

    """
    github_data = {
        'user': github.user,
        'repo': github.repo,
    }

    urls = {}

    if include_urls:
        # TODO: Move to helper function
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
            'github': github_data,
            'urls': urls,
        },
        auth=None,
        foreign_user=committer,
        log_date=date,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('github', 'node')
def github_hook_callback(node_addon, **kwargs):
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
                node, node_addon, 'github_' + NodeLog.FILE_ADDED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('modified', []):
            add_hook_log(
                node, node_addon, 'github_' + NodeLog.FILE_UPDATED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('removed', []):
            add_hook_log(
                node, node_addon, 'github_' + NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
