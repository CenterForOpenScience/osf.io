# -*- coding: utf-8 -*-
import httplib as http
from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError, PermissionsError
from website.util import api_url_for
from website.util import permissions
from website.project.decorators import (
    must_have_permission,
    must_have_addon,
    must_not_be_registration,
    must_be_addon_authorizer,
)
from framework.exceptions import HTTPError


from website.addons.googledrive.utils import serialize_urls
from website.addons.googledrive.utils import serialize_settings
from website.addons.googledrive.utils import user_accounts
from website.addons.googledrive.serializer import GoogleDriveSerializer


@must_be_logged_in
@must_have_addon('googledrive', 'node')
@must_have_permission(permissions.WRITE)
def googledrive_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    result = GoogleDriveSerializer(
        node_settings=node_addon,
        user_settings=auth.user.get_addon('googledrive')
    ).serialized_node_settings
    return result


@must_not_be_registration
@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_be_addon_authorizer('googledrive')
@must_have_permission(permissions.WRITE)
def googledrive_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked Google Drive folder/file."""
    selected = request.get_json().get('selected')
    node_addon.set_target_folder(selected, auth=auth)
    import pdb; pdb.set_trace()
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': selected['path'],
            },
            'urls': GoogleDriveSerializer(
                node_settings=node_addon,
                user_settings=auth.user.get_addon('googledrive')
            ).serialized_node_settings
        },
        'message': 'Successfully updated settings.',
    }

@must_be_logged_in
def list_googledrive_user_acccounts(auth):
    """View for getting a JSON representation of the logged-in user's
    Google Drive user settings.
    """
    return GoogleDriveSerializer(user_settings=auth.user.get_addon('googledrive')).serialized_user_settings


@must_have_permission(permissions.WRITE)
@must_have_addon('googledrive', 'node')
def googledrive_import_user_auth(auth, node_addon, **kwargs):
    """Import googledrive credentials from the currently logged-in user to a node.
    """

    user = auth.user
    external_account = [account
                        for account in user.external_accounts
                        if account.provider == 'googledrive']

    # TODO: Make this useful for multiple connected accounts
    try:
        node_addon.set_auth(external_account[0], user)
    except PermissionsError:
        raise HTTPError(http.FORBIDDEN)

    result = GoogleDriveSerializer(
        node_settings=node_addon,
        user_settings=user.get_addon('googledrive'),
    ).serialized_node_settings
    return {'result': result}

@must_have_permission(permissions.WRITE)
@must_have_addon('googledrive', 'node')
def googledrive_remove_user_auth(node_addon, auth, **kwargs):
        user = auth.user
        node_addon.clear_auth()
        node_addon.reload()
        result = GoogleDriveSerializer(
            node_settings=node_addon,
            user_settings=user.get_addon('googledrive'),
        ).serialized_node_settings
        return {'result': result}