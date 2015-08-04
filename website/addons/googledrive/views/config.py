# -*- coding: utf-8 -*-
from flask import request

from framework.auth.decorators import must_be_logged_in

from website.util import api_url_for
from website.util import permissions
from website.project.decorators import (
    must_have_permission,
    must_have_addon,
    must_not_be_registration,
    must_be_addon_authorizer,
)

from website.addons.googledrive.utils import serialize_urls
from website.addons.googledrive.utils import serialize_settings


@must_be_logged_in
@must_have_addon('googledrive', 'node')
@must_have_permission(permissions.WRITE)
def googledrive_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': serialize_settings(node_addon, auth.user),
    }


@must_not_be_registration
@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_be_addon_authorizer('googledrive')
@must_have_permission(permissions.WRITE)
def googledrive_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked Google Drive folder/file."""
    selected = request.get_json().get('selected')
    node_addon.set_folder(selected, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': selected['path'],
            },
            'urls': serialize_urls(node_addon),
        },
        'message': 'Successfully updated settings.',
    }


@must_be_logged_in
def googledrive_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Google Drive user settings.
    """
    urls = {
        'create': api_url_for('googledrive_oauth_start_user'),
        'delete': api_url_for('googledrive_oauth_delete_user'),
    }

    user_addon = auth.user.get_addon('googledrive')

    user_has_auth = False
    username = ''
    if user_addon:
        user_has_auth = user_addon.has_auth
        username = user_addon.username

    return {
        'result': {
            'urls': urls,
            'username': username,
            'userHasAuth': user_has_auth,
        },
    }
