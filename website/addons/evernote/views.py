from flask import request

from framework.auth.decorators import must_be_logged_in
from website.addons.evernote.serializer import EvernoteSerializer
from website.oauth.models import ExternalAccount
from website.util import permissions
from website.project.decorators import (
    must_have_addon,
    must_have_permission
)

import logging
logger = logging.getLogger(__name__)

@must_be_logged_in
def evernote_get_user_settings(auth):
    """ Returns the list of all of the current user's authorized Evernote accounts """
    serializer = EvernoteSerializer(user_settings=auth.user.get_addon('evernote'))
    return serializer.serialized_user_settings


@must_have_addon('evernote', 'node')
@must_have_permission(permissions.WRITE)
def evernote_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    # following from box addon:
    # if node_addon.external_account:
    #     refresh_oauth_key(node_addon.external_account)

    #logger.debug(node_addon)
    return {
        'result': EvernoteSerializer().serialize_settings(node_addon, auth.user),
    }

@must_have_addon('evernote', 'user')
@must_have_addon('evernote', 'node')
@must_have_permission(permissions.WRITE)
def evernote_add_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import evernote credentials from the currently logged-in user to a node.
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
        'result': EvernoteSerializer().serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }
