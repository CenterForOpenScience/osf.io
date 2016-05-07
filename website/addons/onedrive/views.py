"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

import logging

from flask import request
from website.addons.onedrive.client import OneDriveClient

from framework.exceptions import HTTPError, PermissionsError
from framework.auth.decorators import must_be_logged_in

from website.oauth.models import ExternalAccount

from website.util import permissions
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
)

from website.addons.onedrive.serializer import OneDriveSerializer

logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)

@must_be_logged_in
def onedrive_get_user_settings(auth):
    """ Returns the list of all of the current user's authorized OneDrive accounts """
    serializer = OneDriveSerializer(user_settings=auth.user.get_addon('onedrive'))
    return serializer.serialized_user_settings


@must_have_addon('onedrive', 'node')
@must_have_permission(permissions.WRITE)
def onedrive_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': OneDriveSerializer().serialize_settings(node_addon, auth.user),
    }


@must_not_be_registration
@must_have_addon('onedrive', 'user')
@must_have_addon('onedrive', 'node')
@must_be_addon_authorizer('onedrive')
@must_have_permission(permissions.WRITE)
def onedrive_set_config(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked onedrive folder."""
    folder = request.json.get('selected')
    serializer = OneDriveSerializer(node_settings=node_addon)

    logger.debug('folder::' + repr(folder))
    logger.debug('serializer::' + repr(serializer))

    name = folder['name']

    node_addon.set_folder(folder, auth=auth)

    return {
        'result': {
            'folder': {
                'name': name,
                'path': name,
            },
            'urls': serializer.addon_serialized_urls,
        },
        'message': 'Successfully updated settings.',
    }


@must_have_addon('onedrive', 'user')
@must_have_addon('onedrive', 'node')
@must_have_permission(permissions.WRITE)
def onedrive_add_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import onedrive credentials from the currently logged-in user to a node.
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
        'result': OneDriveSerializer().serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }


@must_not_be_registration
@must_have_addon('onedrive', 'node')
@must_have_permission(permissions.WRITE)
def onedrive_remove_user_auth(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()


@must_have_addon('onedrive', 'user')
@must_have_addon('onedrive', 'node')
@must_have_permission(permissions.WRITE)
def onedrive_get_share_emails(auth, user_addon, node_addon, **kwargs):
    """Return a list of emails of the contributors on a project.

    The current user MUST be the user who authenticated OneDrive for the node.
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


@must_have_addon('onedrive', 'node')
@must_be_addon_authorizer('onedrive')
def onedrive_folder_list(node_addon, **kwargs):
    """Returns a list of folders in OneDrive"""
    if not node_addon.has_auth:
        raise HTTPError(http.FORBIDDEN)

    node = node_addon.owner
    folder_id = request.args.get('folderId')
    logger.debug('oauth_provider::' + repr(node_addon.oauth_provider))
    logger.debug('fetch_access_token::' + repr(node_addon))
    logger.debug('node_addon.external_account::' + repr(node_addon.external_account))
    logger.debug('node_addon.external_account::oauth_key' + repr(node_addon.external_account.oauth_key))
    logger.debug('node_addon.external_account::expires_at' + repr(node_addon.external_account.refresh_token))
    logger.debug('node_addon.external_account::expires_at' + repr(node_addon.external_account.expires_at))

    if folder_id is None:
        return [{
            'id': '0',
            'path': 'All Files',
            'addon': 'onedrive',
            'kind': 'folder',
            'name': '/ (Full OneDrive)',
            'urls': {
                'folders': node.api_url_for('onedrive_folder_list', folderId=0),
            }
        }]

    if folder_id == '0':
        folder_id = 'root'

    access_token = node_addon.fetch_access_token()
    logger.debug('access_token::' + repr(access_token))

    oneDriveClient = OneDriveClient(access_token)
    items = oneDriveClient.folders(folder_id)
    logger.debug('folders::' + repr(items))

    return [
        {
            'addon': 'onedrive',
            'kind': 'folder',
            'id': item['id'],
            'name': item['name'],
            'path': item['name'],
            'urls': {
                'folders': node.api_url_for('onedrive_folder_list', folderId=item['id']),
            }
        }
        for item in items

    ]
