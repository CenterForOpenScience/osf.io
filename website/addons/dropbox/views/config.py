"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging
import httplib as http

from framework import request
from framework.auth import get_current_user
from website.project.decorators import (must_have_addon,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)
from framework.exceptions import HTTPError

from website.addons.dropbox.client import get_node_addon_client

logger = logging.getLogger(__name__)
debug = logger.debug


@must_be_valid_project
@must_have_addon('dropbox', 'node')
def dropbox_config_get(node_addon, **kwargs):
    user = get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
        'status': 200
    }, 200


def serialize_folder(metadata):
    """Serializes metadata to a simple dict with the display name and path
    of the folder.
    """
    # if path is root
    if metadata['path'] == '' or metadata['path'] == '/':
        name = '/ (Full Dropbox)'
    else:
        name = 'Dropbox' + metadata['path']
    return {
        'name': name,
        'path': metadata['path']
    }


def get_folders(client):
    """Gets a list of folders in a user's Dropbox, including the root.
    Each folder is represented as a dict with its display name and path.
    """
    metadata = client.metadata('/', list=True)
    # List each folder, including the root
    root = {
        'name': '/ (Full Dropbox)',
        'path': ''
    }
    folders = [root] + [serialize_folder(each)
                        for each in metadata['contents'] if each['is_dir']]
    return folders


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    DropboxNodeSettings record. Provides the return value for the
    dropbox config endpoints.
    """
    node = node_settings.owner
    user_settings = current_user.get_addon('dropbox')
    user_has_auth = user_settings is not None and user_settings.has_auth
    urls = {
        'config': node.api_url_for('dropbox_config_put'),
        'deauthorize': node.api_url_for('dropbox_deauthorize'),
        'auth': node.api_url_for('dropbox_oauth_start'),
        'importAuth': node.api_url_for('dropbox_import_user_auth'),
        'files': node.web_url_for('collect_file_trees__page'),
    }
    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userHasAuth': user_has_auth,
        'urls': urls
    }
    if node_settings.has_auth:
        # Show available folders
        cl = client or get_node_addon_client(node_settings)
        path = node_settings.folder or '/'
        result.update({
            'folders': get_folders(cl),
            'folder':  {
                'name': 'Dropbox' + path,
                'path': path
            },
            'ownerName': node_settings.user_settings.account_info['display_name']
        })
    return result


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked dropbox folder."""
    folder = request.json.get('selected')
    path = folder['path']
    node_addon.set_folder(path, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': 'Dropbox' + path,
                'path': path
            },
        },
        'message': 'Successfully updated settings.',
        'status': 200
    }, 200


@must_have_permission('write')
@must_have_addon('dropbox', 'node')
def dropbox_import_user_auth(auth, node_addon, **kwargs):
    """Import dropbox credentials from the currently logged-in user to a node.
    """
    user = auth.user
    user_addon = user.get_addon('dropbox')
    if user_addon is None or node_addon is None:
        raise HTTPError(http.BAD_REQUEST)
    node_addon.user_settings = user_addon
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
        'status': 200
    }, 200

@must_have_permission('write')
@must_have_addon('dropbox', 'node')
def dropbox_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    return None
