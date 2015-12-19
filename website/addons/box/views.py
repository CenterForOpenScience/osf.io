"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import os
import httplib as http

from box.client import BoxClient, BoxClientException
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError
from website.addons.box.model import Box
from website.addons.base import generic_views
from website.addons.box.serializer import BoxSerializer

SHORT_NAME = 'box'
FULL_NAME = 'Box'

box_account_list = generic_views.account_list(
    SHORT_NAME,
    BoxSerializer
)

box_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BoxSerializer
)

def _get_folders(node_addon, folder_id):
    node = node_addon.owner
    if folder_id is None:
        return [{
            'id': '0',
            'path': 'All Files',
            'addon': 'box',
            'kind': 'folder',
            'name': '/ (Full Box)',
            'urls': {
                'folders': node.api_url_for('box_folder_list', folderId=0),
            }
        }]

    try:
        Box(node_addon.external_account).refresh_oauth_key()
        client = BoxClient(node_addon.external_account.oauth_key)
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
                'folders': node.api_url_for('box_folder_list', folderId=item['id']),
            }
        }
        for item in metadata['item_collection']['entries']
        if item['type'] == 'folder'
    ]

box_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

box_get_config = generic_views.get_config(
    SHORT_NAME,
    BoxSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

box_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    BoxSerializer,
    _set_folder
)

box_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

box_root_folder = generic_views.root_folder(
    SHORT_NAME
)
