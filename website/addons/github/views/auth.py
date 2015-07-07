from flask import request
import httplib as http
from framework.exceptions import HTTPError, PermissionsError
from website.oauth.models import ExternalAccount

from website.project.decorators import (
    must_have_permission,
    must_not_be_registration,
    must_have_addon,
)
from website.addons.github.serializer import GitHubSerializer

@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_add_user_auth(auth, node_addon, **kwargs):
    """Allows for importing existing auth to GithubNodeSettings """
    user = auth.user
    external_account_id = request.get_json().get('external_account_id')
    external_account = ExternalAccount.load(external_account_id)
    if external_account not in user.external_accounts:
            raise HTTPError(http.FORBIDDEN)

    try:
        node_addon.set_auth(external_account, user)
    except PermissionsError:
        raise HTTPError(http.FORBIDDEN)

    return GitHubSerializer(
        node_settings=node_addon,
        user_settings=user.get_addon('github'),
    ).serialized_node_settings

@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_remove_user_auth(auth, node_addon, **kwargs):
    """Removes auth from GithubNodeSettings """

    node_addon.clear_auth()
    return GitHubSerializer(
        node_settings=node_addon,
        user_settings=auth.user.get_addon('github'),
    ).serialized_node_settings
