import httplib as http
from framework.exceptions import HTTPError
from ..api import GitHub


MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}


def _get_refs(addon, branch=None, sha=None, connection=None):
    """Get the appropriate branch name and sha given the addon settings object,
    and optionally the branch and sha from the request arguments.

    :param str branch: Branch name. If None, return the default branch from the
        repo settings.
    :param str sha: The SHA.
    :param GitHub connection: GitHub API object. If None, one will be created
        from the addon's user settings.

    """
    connection = connection or GitHub.from_settings(addon.user_settings)

    if sha and not branch:
        raise HTTPError(http.BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        repo = connection.repo(addon.user, addon.repo)
        if repo is None:
            return None, None, None
        branch = repo['default_branch']

    # Get registered branches if provided
    registered_branches = (
        addon.registration_data.get('branches', [])
        if addon.owner.is_registration
        else []
    )
    registered_branch_names = [
        each['name']
        for each in registered_branches
    ]

    # Fail if registered and branch not in registration data
    if registered_branches and branch not in registered_branch_names:
        raise HTTPError(http.BAD_REQUEST)

    # Get data from GitHub API if not registered
    branches = registered_branches or connection.branches(addon.user, addon.repo)

    # Use registered SHA if provided
    if registered_branches:
        for each in registered_branches:
            if branch == each['name']:
                sha = each['commit']['sha']
                break
    elif sha is None:
        branch_json = connection.branches(addon.user, addon.repo, branch)
        if branch_json:
            sha = branch_json['commit']['sha']

    return branch, sha, branches


def _check_permissions(node_settings, user, connection, branch, sha=None, repo=None):

    user_settings = node_settings.user_settings
    has_access = False

    has_auth = bool(user_settings and user_settings.has_auth)
    if has_auth:
        repo = repo or connection.repo(
            node_settings.user, node_settings.repo
        )
        has_access = (
            repo is not None and (
                'permissions' not in repo or
                repo['permissions']['push']
            )
        )

    if sha:
        branches = connection.branches(
            node_settings.user, node_settings.repo, branch
        )
        is_head = sha == branches['commit']['sha']
    else:
        is_head = True

    can_edit = (
        node_settings.owner.can_edit(user) and
        not node_settings.owner.is_registration and
        has_access and
        is_head
    )

    return can_edit
