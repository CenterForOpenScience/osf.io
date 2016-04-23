from flask import request
import httplib as http

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError, PermissionsError

from website.addons.base import generic_views
from website.addons.dmptool import utils
from website.addons.dmptool.model import DmptoolProvider
from website.addons.dmptool.serializer import DmptoolSerializer
from website.oauth.models import ExternalAccount
from website.util import permissions
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon,
    must_be_addon_authorizer,
    must_not_be_registration,
    must_have_permission
)

import logging
logger = logging.getLogger(__name__)

SHORT_NAME = 'dmptool'
FULL_NAME = 'DMPTool'

@must_be_logged_in
def dmptool_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    user = auth.user
    provider = dmptoolProvider()

    host = request.json.get('host').rstrip('/')
    api_token = request.json.get('api_token')

    # Verify that credentials are valid
    client.connect_or_error(host, api_token)

    # Note: `dmptoolSerializer` expects display_name to be a URL
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,       # no username; show host
            oauth_key=host,          # hijacked; now host
            oauth_secret=api_token,  # hijacked; now api_token
            provider_id=api_token,   # Change to username if dmptool allows
        )
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', api_token)
        )

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)

    user_addon = auth.user.get_addon('dmptool')
    if not user_addon:
        user.add_addon('dmptool')
    user.save()

    # Need to ensure that the user has dmptool enabled at this point
    user.get_or_add_addon('dmptool', auth=auth)
    user.save()

    return {}


@must_be_logged_in
def dmptool_get_user_settings(auth):
    """ Returns the list of all of the current user's authorized dmptool accounts """
    serializer = DmptoolSerializer(user_settings=auth.user.get_addon('dmptool'))
    return serializer.serialized_user_settings


@must_have_addon('dmptool', 'node')
@must_have_permission(permissions.WRITE)
def dmptool_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    # following from box addon:
    # if node_addon.external_account:
    #     refresh_oauth_key(node_addon.external_account)

    #logger.debug(node_addon)
    return {
        'result': DmptoolSerializer().serialize_settings(node_addon, auth.user),
    }

@must_not_be_registration
@must_have_addon('dmptool', 'user')
@must_have_addon('dmptool', 'node')
@must_be_addon_authorizer('dmptool')
@must_have_permission(permissions.WRITE)
def dmptool_set_config(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked dmptool folder."""
    serializer = DmptoolSerializer(node_settings=node_addon)

    return {
        'result': {
        },
        'message': 'Successfully updated settings.',
    }


@must_have_addon('dmptool', 'user')
@must_have_addon('dmptool', 'node')
@must_have_permission(permissions.WRITE)
def dmptool_add_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import dmptool credentials from the currently logged-in user to a node.
    """
    external_account = ExternalAccount.load(
        request.json['external_account_id']
    )

    if external_account not in user_addon.external_accounts:
        raise HTTPError(http.FORBIDDEN)

    try:
        node_addon.set_auth(external_account, user_addon.owner)
    except PermissionsError:
        raise HTTPError(http.FORBIDDEN)

    node_addon.set_user_auth(user_addon)
    node_addon.save()

    return {
        'result': DmptoolSerializer().serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }


dmptool_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)


@must_be_contributor_or_public
@must_have_addon('dmptool', 'node')
def dmptool_widget(node_addon, **kwargs):
    """Collects and serializes settting needed to build the widget."""

    #provider = ZoteroCitationsProvider()
    #return provider.widget(node_addon)

    ret = node_addon.config.to_json()
    ret.update({
        'complete': node_addon.complete
    })

    return ret
