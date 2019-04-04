import hmac
import uuid
from future.moves.urllib.parse import unquote_plus
import hashlib
from rest_framework import status as http_status
from github3.repos.branch import Branch

from framework.exceptions import HTTPError
from addons.base.exceptions import HookError

from addons.github.api import GitHubClient

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'move': 'Moved {0}'.format(MESSAGE_BASE),
    'copy': 'Copied {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}


def make_hook_secret():
    return str(uuid.uuid4()).replace('-', '')


HOOK_SIGNATURE_KEY = 'X-Hub-Signature'
def verify_hook_signature(node_settings, data, headers):
    """Verify hook signature.
    :param GithubNodeSettings node_settings:
    :param dict data: JSON response body
    :param dict headers: Request headers
    :raises: HookError if signature is missing or invalid
    """
    if node_settings.hook_secret is None:
        raise HookError('No secret key')
    digest = hmac.new(
        str(node_settings.hook_secret),
        data,
        digestmod=hashlib.sha1
    ).hexdigest()
    signature = headers.get(HOOK_SIGNATURE_KEY, '').replace('sha1=', '')
    if digest != signature:
        raise HookError('Invalid signature')


def get_path(kwargs, required=True):
    path = kwargs.get('path')
    if path:
        return unquote_plus(path)
    elif required:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)


def get_refs(addon, branch=None, sha=None, connection=None):
    """Get the appropriate branch name and sha given the addon settings object,
    and optionally the branch and sha from the request arguments.
    :param str branch: Branch name. If None, return the default branch from the
        repo settings.
    :param str sha: The SHA.
    :param GitHub connection: GitHub API object. If None, one will be created
        from the addon's user settings.
    """
    connection = connection or GitHubClient(external_account=addon.external_account)

    if sha and not branch:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        repo = connection.repo(addon.user, addon.repo)
        if repo is None:
            return None, None, None
        branch = repo.default_branch
    # Get registered branches if provided
    registered_branches = (
        [Branch.from_json(b) for b in addon.registration_data.get('branches', [])]
        if addon.owner.is_registration
        else []
    )

    registered_branch_names = [
        each.name
        for each in registered_branches
    ]
    # Fail if registered and branch not in registration data
    if registered_branches and branch not in registered_branch_names:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Get data from GitHub API if not registered
    branches = registered_branches or connection.branches(addon.user, addon.repo)

    # Use registered SHA if provided
    for each in branches:
        if branch == each.name:
            sha = each.commit.sha
            break
    return branch, sha, branches


def check_permissions(node_settings, auth, connection, branch, sha=None, repo=None):

    user_settings = node_settings.user_settings
    has_access = False

    has_auth = bool(user_settings and user_settings.has_auth)
    if has_auth:
        repo = repo or connection.repo(
            node_settings.user, node_settings.repo
        )

        has_access = (
            repo is not None and (
                repo.permissions and repo.permissions['push']
            )
        )

    if sha:
        branches = connection.branches(
            node_settings.user, node_settings.repo, branch
        )
        # TODO Will I ever return false?
        is_head = next((True for branch in branches if sha == branch.commit.sha), None)
    else:
        is_head = True

    can_edit = (
        node_settings.owner.can_edit(auth) and
        not node_settings.owner.is_registration and
        has_access and
        is_head
    )

    return can_edit
