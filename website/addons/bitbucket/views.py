"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from dateutil.parser import parse as dateparse
import httplib as http
import logging

from flask import request, make_response

from framework.exceptions import HTTPError

from website.addons.base import generic_views
from website.addons.bitbucket.api import BitbucketClient, ref_to_params
from website.addons.bitbucket.exceptions import NotFoundError, BitbucketError
from website.addons.bitbucket.serializer import BitbucketSerializer
from website.addons.bitbucket.utils import (
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

logger = logging.getLogger(__name__)

logging.getLogger('bitbucket3').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)

SHORT_NAME = 'bitbucket'
FULL_NAME = 'Bitbucket'

############
# Generics #
############

bitbucket_account_list = generic_views.account_list(
    SHORT_NAME,
    BitbucketSerializer
)

bitbucket_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BitbucketSerializer
)

def _get_folders(node_addon, folder_id):
    pass

bitbucket_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

bitbucket_get_config = generic_views.get_config(
    SHORT_NAME,
    BitbucketSerializer
)

bitbucket_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

bitbucket_root_folder = generic_views.root_folder(
    SHORT_NAME
)

#################
# Special Cased #
#################

@must_not_be_registration
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission('write')
def bitbucket_set_config(auth, **kwargs):
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
    bitbucket_user_name = request.json.get('bitbucket_user', '')
    bitbucket_repo_name = request.json.get('bitbucket_repo', '')

    if not bitbucket_user_name or not bitbucket_repo_name:
        raise HTTPError(http.BAD_REQUEST)

    # Verify that repo exists and that user can access
    connection = BitbucketClient(external_account=node_settings.external_account)
    repo = connection.repo(bitbucket_user_name, bitbucket_repo_name)
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
        bitbucket_user_name != node_settings.user or
        bitbucket_repo_name != node_settings.repo
    )

    # Update hooks
    if changed:

        # Delete existing hook, if any
        node_settings.delete_hook()

        # Update node settings
        node_settings.user = bitbucket_user_name
        node_settings.repo = bitbucket_repo_name

        # Log repo select
        node.add_log(
            action='bitbucket_repo_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'bitbucket': {
                    'user': bitbucket_user_name,
                    'repo': bitbucket_repo_name,
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
@must_have_addon('bitbucket', 'node')
def bitbucket_download_starball(node_addon, **kwargs):

    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('sha', 'master')

    connection = BitbucketClient(external_account=node_addon.external_account)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, archive, ref
    )

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp

#########
# HGrid #
#########

@must_be_contributor_or_public
@must_have_addon('bitbucket', 'node')
def bitbucket_root_folder(*args, **kwargs):
    """View function returning the root container for a Bitbucket repo. In
    contrast to other add-ons, this is exposed via the API for Bitbucket to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return bitbucket_hgrid_data(node_settings, auth=auth, **data)

def bitbucket_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = BitbucketClient(external_account=node_settings.external_account)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public and not node.is_contributor(auth.user):
        try:
            repo = connection.repo(node_settings.user, node_settings.repo)
        except NotFoundError:
            # TODO: Test me @jmcarp
            # TODO: Add warning message
            logger.error('Could not access Bitbucket repo')
            return None
        if repo.private:
            return None

    try:
        branch, sha, branches = get_refs(
            node_settings,
            branch=kwargs.get('branch'),
            sha=kwargs.get('sha'),
            connection=connection,
        )
    except (NotFoundError, BitbucketError):
        # TODO: Show an alert or change Bitbucket configuration?
        logger.error('Bitbucket repo not found')
        return

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = check_permissions(
            node_settings, auth, connection, branch, sha, repo=repo,
        )
    else:
        ref = None
        can_edit = False

    name_tpl = '{user}/{repo}'.format(
        user=node_settings.user, repo=node_settings.repo
    )

    permissions = {
        'edit': can_edit,
        'view': True,
        'private': node_settings.is_private
    }
    urls = {
        'upload': node_settings.owner.api_url + 'bitbucket/file/' + (ref or ''),
        'fetch': node_settings.owner.api_url + 'bitbucket/hgrid/' + (ref or ''),
        'branch': node_settings.owner.api_url + 'bitbucket/hgrid/root/',
        'zip': node_settings.owner.api_url + 'bitbucket/zipball/' + (ref or ''),
        'repo': 'https://bitbucket.com/{0}/{1}/tree/{2}'.format(node_settings.user, node_settings.repo, branch)
    }

    branch_names = [each.name for each in branches]
    if not branch_names:
        branch_names = [branch]  # if repo un-init-ed then still add default branch to list of branches

    return [rubeus.build_addon_root(
        node_settings,
        name_tpl,
        urls=urls,
        permissions=permissions,
        branches=branch_names,
        defaultBranch=branch,
        private_key=kwargs.get('view_only', None),
    )]

#########
# Repos #
#########

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission('write')
def bitbucket_create_repo(**kwargs):
    repo_name = request.json.get('name')
    if not repo_name:
        raise HTTPError(http.BAD_REQUEST)

    node_settings = kwargs['node_addon']
    connection = BitbucketClient(external_account=node_settings.external_account)

    try:
        repo = connection.create_repo(repo_name, auto_init=True)
    except BitbucketError:
        # TODO: Check status code
        raise HTTPError(http.BAD_REQUEST)

    return {
        'user': repo.owner.login,
        'repo': repo.name,
    }

#########
# Hooks #
#########

# TODO: Refactor using NodeLogger
def add_hook_log(node, bitbucket, action, path, date, committer, include_urls=False,
                 sha=None, save=False):
    """Add log event for commit from webhook payload.

    :param node: Node to add logs to
    :param bitbucket: Bitbucket node settings record
    :param path: Path to file
    :param date: Date of commit
    :param committer: Committer name
    :param include_urls: Include URLs in `params`
    :param sha: SHA of updated file
    :param save: Save changes

    """
    bitbucket_data = {
        'user': bitbucket.user,
        'repo': bitbucket.repo,
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
            'bitbucket': bitbucket_data,
            'urls': urls,
        },
        auth=None,
        foreign_user=committer,
        log_date=date,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('bitbucket', 'node')
def bitbucket_hook_callback(node_addon, **kwargs):
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
                node, node_addon, 'bitbucket_' + NodeLog.FILE_ADDED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('modified', []):
            add_hook_log(
                node, node_addon, 'bitbucket_' + NodeLog.FILE_UPDATED,
                path, date, committer, include_urls=True, sha=_id,
            )
        for path in commit.get('removed', []):
            add_hook_log(
                node, node_addon, 'bitbucket_' + NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
