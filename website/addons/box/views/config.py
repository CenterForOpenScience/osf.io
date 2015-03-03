"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import os
import httplib as http

from flask import request
from box.client import BoxClientException
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError

from website.util import web_url_for
from website.util import permissions
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
)

from website.addons.box.client import get_node_client
from website.addons.box.client import get_client_from_user_settings


@must_have_addon('box', 'node')
@must_have_permission(permissions.WRITE)
def box_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': serialize_settings(node_addon, auth.user),
    }


def serialize_folder(metadata):
    """Serializes metadata to a dict with the display name and path
    of the folder.
    """
    # if path is root
    if metadata['path'] == '' or metadata['path'] == '/':
        name = 'All Files'
    else:
        name = 'Box' + metadata['path']
    return {
        'name': name,
        'path': metadata['path'],
    }


def get_folders(client):
    """Gets a list of folders in a user's Box, including the root.
    Each folder is represented as a dict with its display name and path.
    """
    metadata = client.metadata('/', list=True)
    # List each folder, including the root
    root = {
        'name': 'All Files',
        'path': '',
    }
    folders = [root] + [
        serialize_folder(each)
        for each in metadata['contents'] if each['is_dir']
    ]
    return folders


def serialize_urls(node_settings):
    node = node_settings.owner

    urls = {
        'settings': web_url_for('user_addons'),
        'auth': node.api_url_for('box_oauth_start'),
        'config': node.api_url_for('box_config_put'),
        'files': node.web_url_for('collect_file_trees'),
        'emails': node.api_url_for('box_get_share_emails'),
        'deauthorize': node.api_url_for('box_deauthorize'),
        'importAuth': node.api_url_for('box_import_user_auth'),
        # Endpoint for fetching only folders (including root)
        'folders': node.api_url_for('box_list_folders'),
    }
    return urls


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    BoxNodeSettings record. Provides the return value for the
    box config endpoints.
    """
    valid_credentials = True
    user_settings = node_settings.user_settings
    current_user_settings = current_user.get_addon('box')
    user_is_owner = user_settings is not None and user_settings.owner == current_user

    if user_settings:
        try:
            client = client or get_client_from_user_settings(user_settings)
            client.get_user_info()
        except BoxClientException:
            valid_credentials = False

    result = {
        'userIsOwner': user_is_owner,
        'nodeHasAuth': node_settings.has_auth,
        'urls': serialize_urls(node_settings),
        'validCredentials': valid_credentials,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
    }

    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for(
            'profile_view_id',
            uid=user_settings.owner._id
        )
        result['ownerName'] = user_settings.owner.fullname
        # Show available folders
        # path = node_settings.folder

        if node_settings.folder_id is None:
            result['folder'] = {'name': None, 'path': None}
        elif valid_credentials:
            path = node_settings.fetch_full_folder_path()

            result['folder'] = {
                'path': path,
                'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full Box)'
            }
    return result


@must_not_be_registration
@must_have_addon('box', 'user')
@must_have_addon('box', 'node')
@must_be_addon_authorizer('box')
@must_have_permission(permissions.WRITE)
def box_config_put(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked box folder."""
    folder = request.json.get('selected')

    uid = folder['id']
    path = folder['path']

    node_addon.set_folder(uid, auth=auth)

    return {
        'result': {
            'folder': {
                'name': path,
                'path': path,
            },
            'urls': serialize_urls(node_addon),
        },
        'message': 'Successfully updated settings.',
    }


@must_have_addon('box', 'user')
@must_have_addon('box', 'node')
@must_have_permission(permissions.WRITE)
def box_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import box credentials from the currently logged-in user to a node.
    """
    node_addon.set_user_auth(user_addon)
    node_addon.save()

    return {
        'result': serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }


@must_not_be_registration
@must_have_addon('box', 'node')
@must_have_permission(permissions.WRITE)
def box_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()


@must_have_addon('box', 'user')
@must_have_addon('box', 'node')
@must_have_permission(permissions.WRITE)
def box_get_share_emails(auth, user_addon, node_addon, **kwargs):
    """Return a list of emails of the contributors on a project.

    The current user MUST be the user who authenticated Box for the node.
    """
    if not node_addon.user_settings:
        raise HTTPError(http.BAD_REQUEST)
    # Current user must be the user who authorized the addon
    if node_addon.user_settings.owner != auth.user:
        raise HTTPError(http.FORBIDDEN)

    return {
        'result': {
            'emails': [
                contrib.username
                for contrib in node_addon.owner.contributors
                if contrib != auth.user
            ],
        }
    }


@must_have_addon('box', 'node')
@must_be_addon_authorizer('box')
def box_list_folders(node_addon, **kwargs):
    """Returns a list of folders in Box"""
    if not node_addon.has_auth:
        raise HTTPError(http.FORBIDDEN)

    node = node_addon.owner
    folder_id = request.args.get('folderId')

    if folder_id is None:
        return [{
            'id': '0',
            'path': 'All Files',
            'addon': 'box',
            'kind': 'folder',
            'name': '/ (Full Box)',
            'urls': {
                'folders': node.api_url_for('box_list_folders', folderId=0),
            }
        }]

    try:
        client = get_node_client(node)
    except BoxClientException:
        raise HTTPError(http.FORBIDDEN)

    try:
        metadata = client.get_folder(folder_id)
    except BoxClientException:
        raise HTTPError(http.NOT_FOUND)
    except MaxRetryError:
        raise HTTPError(http.BAD_REQUEST)

    # Raise error if folder was deleted
    if metadata.get('is_deleted'):
        raise HTTPError(http.NOT_FOUND)

    folder_path = '/'.join(
        [
            x['name']
            for x in metadata['path_collection']['entries']
        ] + [metadata['name']]
    )

    return [
        {
            'addon': 'box',
            'kind': 'folder',
            'id': item['id'],
            'name': item['name'],
            'path': os.path.join(folder_path, item['name']),
            'urls': {
                'folders': node.api_url_for('box_list_folders', folderId=item['id']),
            }
        }
        for item in metadata['item_collection']['entries']
        if item['type'] == 'folder'
    ]
