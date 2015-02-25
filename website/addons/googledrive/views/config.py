# -*- coding: utf-8 -*-
import httplib as http

from flask import request

from framework.auth.core import _get_current_user
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import (
    must_have_permission,
    must_have_addon,
    must_not_be_registration,
    must_be_addon_authorizer,
)
from website.util import api_url_for
from website.util import permissions

from ..utils import serialize_settings, serialize_urls


@must_have_addon('googledrive', 'node')
@must_have_permission(permissions.WRITE)
def googledrive_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = _get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK


@must_have_permission(permissions.WRITE)
@must_not_be_registration
@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_be_addon_authorizer('googledrive')
def googledrive_config_put(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked Google Drive folder/file."""
    selected = request.json.get('selected')
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
    }, http.OK


@must_be_logged_in
@must_have_addon('googledrive', 'user')
def googledrive_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Google Drive user settings.
    """
    urls = {
        'create': api_url_for('googledrive_oauth_start_user'),
        'delete': api_url_for('googledrive_oauth_delete_user'),
    }

    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'urls': urls,
            'username': user_addon.username
        },
    }, http.OK
