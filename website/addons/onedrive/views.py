"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

import logging

from flask import request
from website.addons.onedrive.client import OneDriveClient

from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
)

from website.addons.base import generic_views
from website.addons.onedrive.serializer import OneDriveSerializer

logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)

SHORT_NAME = 'onedrive'
FULL_NAME = 'Microsoft OneDrive'

onedrive_account_list = generic_views.account_list(
    SHORT_NAME,
    OneDriveSerializer
)

onedrive_get_config = generic_views.get_config(
    SHORT_NAME,
    OneDriveSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

onedrive_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    OneDriveSerializer,
    _set_folder
)

onedrive_import_auth = generic_views.import_auth(
    SHORT_NAME,
    OneDriveSerializer
)

onedrive_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
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
