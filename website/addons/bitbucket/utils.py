import hmac
import uuid
import urllib
import hashlib
import httplib as http

from framework.exceptions import HTTPError
from website.addons.base.exceptions import HookError

from website.addons.bitbucket.api import BitbucketClient


def make_hook_secret():
    return str(uuid.uuid4()).replace('-', '')


HOOK_SIGNATURE_KEY = 'X-Hub-Signature'
def verify_hook_signature(node_settings, data, headers):
    """Verify hook signature.
    :param BitbucketNodeSettings node_settings:
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
        return urllib.unquote_plus(path)
    elif required:
        raise HTTPError(http.BAD_REQUEST)


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
        raise HTTPError(http.BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        branch = connection.get_repo_default_branch(addon.user, addon.repo)
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
