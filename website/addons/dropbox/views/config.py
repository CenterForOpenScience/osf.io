"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)
from website.util import web_url_for

from website.addons.dropbox import utils
from website.addons.dropbox.client import get_client_from_user_settings
from dropbox.rest import ErrorResponse


@collect_auth
@must_be_valid_project
@must_have_addon('dropbox', 'node')
def dropbox_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': serialize_settings(node_addon, auth.user),
    }, http.OK


def serialize_folder(metadata):
    """Serializes metadata to a dict with the display name and path
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


def serialize_urls(node_settings):
    node = node_settings.owner
    if node_settings.folder and node_settings.folder != '/':
        # The link to share a the folder with other Dropbox users
        share_url = utils.get_share_folder_uri(node_settings.folder)
    else:
        share_url = None

    urls = {
        'config': node.api_url_for('dropbox_config_put'),
        'deauthorize': node.api_url_for('dropbox_deauthorize'),
        'auth': node.api_url_for('dropbox_oauth_start'),
        'importAuth': node.api_url_for('dropbox_import_user_auth'),
        'files': node.web_url_for('collect_file_trees'),
        # Endpoint for fetching only folders (including root)
        'folders': node.api_url_for('dropbox_hgrid_data_contents',
            foldersOnly=1, includeRoot=1),
        'share': share_url,
        'emails': node.api_url_for('dropbox_get_share_emails'),
        'settings': web_url_for('user_addons')
    }
    return urls


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    DropboxNodeSettings record. Provides the return value for the
    dropbox config endpoints.
    """
    user_settings = node_settings.user_settings
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )
    current_user_settings = current_user.get_addon('dropbox')
    valid_credentials = True

    if user_settings:
        try:
            client = client or get_client_from_user_settings(user_settings)
            client.account_info()
        except ErrorResponse as error:
            if error.status == 401:
                valid_credentials = False
            else:
                raise HTTPError(http.BAD_REQUEST)

    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        'validCredentials': valid_credentials,
        'urls': serialize_urls(node_settings),
    }

    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result['ownerName'] = user_settings.owner.fullname
        # Show available folders
        path = node_settings.folder
        if path is None:
            result['folder'] = {'name': None, 'path': None}
        else:
            result['folder'] = {
                'name': 'Dropbox' + path,
                'path': path
            }
    return result


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
@must_be_addon_authorizer('dropbox')
def dropbox_config_put(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked dropbox folder."""
    folder = request.json.get('selected')
    path = folder['path']
    node_addon.set_folder(path, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': 'Dropbox' + path,
                'path': path,
            },
            'urls': serialize_urls(node_addon),
        },
        'message': 'Successfully updated settings.',
    }, http.OK


@must_have_permission('write')
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
def dropbox_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import dropbox credentials from the currently logged-in user to a node.
    """
    user = auth.user
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK

@must_have_permission('write')
@must_have_addon('dropbox', 'node')
@must_not_be_registration
def dropbox_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    return None

@must_have_permission('write')
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
def dropbox_get_share_emails(auth, user_addon, node_addon, **kwargs):
    """Return a list of emails of the contributors on a project.

    The current user MUST be the user who authenticated Dropbox for the node.
    """
    if not node_addon.user_settings:
        raise HTTPError(http.BAD_REQUEST)
    # Current user must be the user who authorized the addon
    if node_addon.user_settings.owner != auth.user:
        raise HTTPError(http.FORBIDDEN)
    result = {
        'emails': [contrib.username
                    for contrib in node_addon.owner.contributors
                        if contrib != auth.user],
        'url': utils.get_share_folder_uri(node_addon.folder)
    }
    return {'result': result}, http.OK
