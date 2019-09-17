"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from dateutil.parser import parse as dateparse
from rest_framework import status as http_status
import logging
import gitlab

from django.core.exceptions import ValidationError
from flask import request, make_response

from framework.exceptions import HTTPError

from addons.base import generic_views
from addons.gitlab.api import GitLabClient
from addons.gitlab.apps import gitlab_hgrid_data
from addons.gitlab.settings import DEFAULT_HOSTS
from addons.gitlab.serializer import GitLabSerializer
from addons.gitlab.utils import verify_hook_signature, MESSAGES
from framework.auth.decorators import must_be_logged_in
from osf.models import ExternalAccount, NodeLog
from osf.utils.permissions import WRITE
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public, must_be_valid_project,
)
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
    }, http_status.HTTP_200_OK

@must_be_logged_in
def gitlab_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""

    host = request.json.get('host').rstrip('/')
    access_token = request.json.get('access_token')

    client = GitLabClient(access_token=access_token, host=host)

    user = client.user()

    try:
        account = ExternalAccount(
            provider='gitlab',
            provider_name='GitLab',
            display_name=user.username,
            oauth_key=access_token,
            oauth_secret=host,  # Hijacked to allow multiple hosts
            provider_id=user.web_url,   # unique for host/username
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider='gitlab', provider_id=user.web_url
        )
        if account.oauth_key != access_token:
            account.oauth_key = access_token
            account.save()

    user = auth.user
    if not user.external_accounts.filter(id=account.id).exists():
        user.external_accounts.add(account)

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
@must_have_permission(WRITE)
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
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Parse request
    gitlab_user_name = request.json.get('gitlab_user', '')
    gitlab_repo_name = request.json.get('gitlab_repo', '')
    gitlab_repo_id = request.json.get('gitlab_repo_id', '')

    if not gitlab_user_name or not gitlab_repo_name or not gitlab_repo_id:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Verify that repo exists and that user can access
    connection = GitLabClient(external_account=node_settings.external_account)

    try:
        repo = connection.repo(gitlab_repo_id)
    except gitlab.exceptions.GitlabError as exc:
        if exc.response_code == 403 and 'must accept the Terms of Service' in exc.error_message:
            return {'message': 'Your gitlab account does not have proper authentication. Ensure you have agreed to Gitlab\'s '
                     'current Terms of Service by disabling and re-enabling your account.'}, http_status.HTTP_400_BAD_REQUEST

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

    ref = request.args.get('branch', 'master')

    connection = GitLabClient(external_account=node_addon.external_account)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, node_addon.repo_id, ref
    )

    resp = make_response(data)
    for key, value in headers.items():
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

#########
# Repos #
#########

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
            'view': '{0}?branch={1}'.format(url, sha),
            'download': '{0}?action=download&branch={1}'.format(url, sha)
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
