import hmac
import uuid
from future.moves.urllib.parse import unquote_plus
import hashlib
from rest_framework import status as http_status

from framework.exceptions import HTTPError
from addons.base.exceptions import HookError

from addons.gitlab.api import GitLabClient

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
    :param GitLabNodeSettings node_settings:
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
    :param GitLab connection: GitLab API object. If None, one will be created
        from the addon's user settings.
    """
    connection = connection or GitLabClient(external_account=addon.external_account)

    if sha and not branch:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        repo = connection.repo(addon.repo_id)
        if repo is None:
            return None, None, None

        branch = repo.default_branch
    # Get data from GitLab API if not registered
    branches = connection.branches(addon.repo_id)

    # Use registered SHA if provided
    for each in branches:
        if branch == each.name:
            sha = each.commit['id']
            break

    return branch, sha, branches


def check_permissions(node_settings, auth, connection, branch, sha=None, repo=None):

    user_settings = node_settings.user_settings
    has_access = False

    has_auth = bool(user_settings and user_settings.has_auth)
    if has_auth:
        repo = repo or connection.repo(node_settings.repo_id)
        project_permissions = repo.permissions.get('project_access') or {}
        group_permissions = repo.permissions.get('group_access') or {}
        has_access = (
            repo is not None and (
                # See https://docs.gitlab.com/ee/api/members.html
                project_permissions.get('access_level', 0) >= 30 or
                group_permissions.get('access_level', 0) >= 30
            )
        )

    if sha:
        current_branch = connection.branches(node_settings.repo_id, branch)
        # TODO Will I ever return false?
        is_head = sha == current_branch.commit['id']
    else:
        is_head = True

    can_edit = (
        node_settings.owner.can_edit(auth) and
        not node_settings.owner.is_registration and
        has_access and
        is_head
    )

    return can_edit
