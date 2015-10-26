"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

import httplib as http
from flask import request
from dropbox.rest import ErrorResponse
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError, PermissionsError
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project,
    must_be_contributor_or_public
)
from website.util import permissions, rubeus
from website.oauth.models import ExternalAccount

from website.addons.dropbox import utils
from website.addons.dropbox.client import (
    get_client_from_user_settings,
    get_node_client,
)
from website.addons.dropbox.serializer import DropboxSerializer


logger = logging.getLogger(__name__)
debug = logger.debug

@must_be_logged_in
def dropbox_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dropbox user settings.
    """
    serializer = DropboxSerializer(user_settings=auth.user.get_addon('dropbox'))
    return serializer.serialized_user_settings

@must_be_logged_in
@must_be_valid_project
@must_have_addon('dropbox', 'node')
def dropbox_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': DropboxSerializer().serialize_settings(node_addon, auth.user)
    }

@must_have_permission(permissions.WRITE)
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
                'name': path if path != '/' else '/ (Full Dropbox)',
                'path': path,
            },
            'urls': DropboxSerializer(
                node_settings=node_addon,
                user_settings=user_addon).addon_serialized_urls
        },
        'message': 'Successfully updated settings.',
    }

@must_have_permission(permissions.WRITE)
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
def dropbox_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import dropbox credentials from the currently logged-in user to a node.
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

    return {
        'result': DropboxSerializer().serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }

@must_not_be_registration
@must_have_addon('dropbox', 'node')
@must_have_permission(permissions.WRITE)
def dropbox_remove_user_auth(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()

@must_have_permission(permissions.WRITE)
@must_have_addon('dropbox', 'node')
@must_not_be_registration
def dropbox_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    return None

@must_have_permission(permissions.WRITE)
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
    return {'result': result}

@must_have_permission(permissions.WRITE)
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
def dropbox_get_folders(auth, node_addon, user_addon, **kwargs):
    """Get a list of Dropbox folders for a user/node pair
    """
    client = get_client_from_user_settings(user_addon)
    return utils.get_folders(client)

@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_hgrid_data_contents(node_addon, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for a folder's contents.

    Takes optional query parameters `foldersOnly` (only return folders) and
    `includeRoot` (include the root folder).
    """
    # No folder, just return an empty list of data
    node = node_addon.owner
    path = kwargs.get('path', '')

    if 'root' in request.args:
        return [{
            'kind': rubeus.FOLDER,
            'path': '/',
            'name': '/ (Full Dropbox)',
            'urls': {
                'folders': node.api_url_for('dropbox_hgrid_data_contents'),
            }
        }]

    # Verify that path is a subdirectory of the node's shared folder
    if not utils.is_authorizer(auth, node_addon):
        utils.abort_if_not_subdir(path, node_addon.folder)

    permissions = {
        'edit': node.can_edit(auth) and not node.is_registration,
        'view': node.can_view(auth)
    }

    client = get_node_client(node)
    file_not_found = HTTPError(http.NOT_FOUND, data=dict(message_short='File not found',
                                                  message_long='The Dropbox file '
                                                  'you requested could not be found.'))

    max_retry_error = HTTPError(http.REQUEST_TIMEOUT, data=dict(message_short='Request Timeout',
                                                   message_long='Dropbox could not be reached '
                                                   'at this time.'))

    try:
        metadata = client.metadata(path)
    except ErrorResponse:
        raise file_not_found
    except MaxRetryError:
        raise max_retry_error

    # Raise error if folder was deleted
    if metadata.get('is_deleted'):
        raise file_not_found

    return [
        utils.metadata_to_hgrid(file_dict, node, permissions) for
        file_dict in metadata['contents'] if file_dict['is_dir']
    ]

def dropbox_addon_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only."""
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder:
        return None
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder,
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]
