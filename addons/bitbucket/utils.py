from future.moves.urllib.parse import unquote_plus
from rest_framework import status as http_status

from framework.exceptions import HTTPError

from addons.bitbucket.api import BitbucketClient


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
    :param Bitbucket connection: Bitbucket API object. If None, one will be created
        from the addon's user settings.
    """
    connection = connection or BitbucketClient(access_token=addon.external_account.oauth_key)

    if sha and not branch:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        branch = connection.repo_default_branch(addon.user, addon.repo)
        if branch is None:
            return None, None, None

    # Get branch list from Bitbucket API
    branches = connection.branches(addon.user, addon.repo)

    # identify commit sha for requested branch
    for each in branches:
        if branch == each['name']:
            sha = each['target']['hash']
            break

    return branch, sha, [
        {'name': x['name'], 'sha': x['target']['hash']}
        for x in branches
    ]
