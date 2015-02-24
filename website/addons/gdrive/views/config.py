# -*- coding: utf-8 -*-
from flask import request
from framework.auth.core import _get_current_user
from framework.auth.decorators import must_be_logged_in, collect_auth
import httplib as http

from website.project.decorators import (must_be_valid_project, must_have_permission,
                                        must_have_addon, must_not_be_registration, must_be_addon_authorizer)
from website.util import api_url_for

from ..utils import serialize_settings, serialize_urls

@collect_auth
@must_be_valid_project
@must_have_addon('gdrive', 'node')
def gdrive_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = _get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('gdrive', 'user')
@must_have_addon('gdrive', 'node')
@must_be_addon_authorizer('gdrive')
def gdrive_config_put(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked Drive folder/file."""
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
@must_have_addon('gdrive', 'user')
def drive_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    GDrive user settings.
    """
    urls = {
        'create': api_url_for('drive_oauth_start_user'),
        'delete': api_url_for('drive_oauth_delete_user'),
    }

    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'urls': urls,
            'username': user_addon.username
        },
    }, http.OK
