# -*- coding: utf-8 -*-

import httplib as http

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.util import web_url_for
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)

from ..api import Figshare
from ..utils import options_to_hgrid


###### AJAX Config
@must_be_logged_in
@must_be_valid_project
@must_have_addon('figshare', 'node')
def figshare_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': serialize_settings(node_addon, auth.user),
    }


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('figshare', 'node')
@must_be_addon_authorizer('figshare')
def figshare_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked figshare folder."""
    fields = request.json.get('selected', {})
    node = node_addon.owner

    name = fields.get('name')
    figshare_id = fields.get('id')
    figshare_type = fields.get('type')

    if not all([name, figshare_id, figshare_type]):
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message='You must supply a name, id, and type'
        ))

    folder = {
        'name': name,
        'id': figshare_id,
        'type': figshare_type,
    }
    node_addon.update_fields(folder, node, auth)
    return {
        'result': {
            'folder': folder,
            'urls': serialize_urls(node_addon),
        },
        'message': 'Successfully updated settings.',
    }


@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_import_user_auth(auth, node_addon, **kwargs):
    """Import figshare credentials from the currently logged-in user to a node.
    """
    user = auth.user
    user_addon = user.get_addon('figshare')
    if user_addon is None or node_addon is None:
        raise HTTPError(http.BAD_REQUEST)
    node_addon.authorize(user_addon, save=True)
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }


@must_have_permission('write')
@must_have_addon('figshare', 'node')
@must_not_be_registration
def figshare_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return {}


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    FigshareNodeSettings record. Provides the return value for the
    figshare config endpoints.
    """

    current_user_settings = current_user.get_addon('figshare')
    user_settings = node_settings.user_settings
    user_has_auth = current_user_settings is not None and current_user_settings.has_auth
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )

    valid_credentials = True
    if user_settings:
        client = client or Figshare.from_settings(user_settings)
        articles, status = client.articles(node_settings)
        if status == 401:
            valid_credentials = False

    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userHasAuth': user_has_auth,
        'userIsOwner': user_is_owner,
        'urls': serialize_urls(node_settings),
        'validCredentials': valid_credentials,
    }

    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result['ownerName'] = user_settings.owner.fullname
        # Show available projects
        linked = node_settings.linked_content or {'id': None, 'type': None, 'name': None}
        result['folder'] = linked
    return result


def serialize_urls(node_settings):
    node = node_settings.owner
    return {
        'config': node.api_url_for('figshare_config_put'),
        'deauthorize': node.api_url_for('figshare_deauthorize'),
        'auth': node.api_url_for('figshare_oauth_start'),
        'importAuth': node.api_url_for('figshare_import_user_auth'),
        'options': node.api_url_for('figshare_get_options'),
        'folders': node.api_url_for('figshare_get_options'),
        'files': node.web_url_for('collect_file_trees'),
        'settings': web_url_for('user_addons')
    }


@must_be_valid_project
@must_have_addon('figshare', 'node')
def figshare_get_options(node_addon, **kwargs):
    options = Figshare.from_settings(node_addon.user_settings).get_options()

    # TODO: Fix error handling
    if options == 401 or not isinstance(options, list):
        raise HTTPError(http.BAD_REQUEST)
        # self.user_settings.remove_auth()
        # push_status_message(messages.OAUTH_INVALID)
    else:
        node = node_addon.owner
        return options_to_hgrid(node, options) or []
