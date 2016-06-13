"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

import httplib as http
from dropbox.rest import ErrorResponse
from dropbox.client import DropboxClient
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError
from website.addons.fedora.serializer import FedoraSerializer
from website.addons.base import generic_views

logger = logging.getLogger(__name__)
debug = logger.debug

SHORT_NAME = 'fedora'
FULL_NAME = 'Fedora'

fedora_account_list = generic_views.account_list(
    SHORT_NAME,
    FedoraSerializer
)

fedora_import_auth = generic_views.import_auth(
    SHORT_NAME,
    FedoraSerializer
)

def _get_folders(node_addon, folder_id):
    node = node_addon.owner
    if folder_id is None:
        return [{
            'id': '/',
            'path': '/',
            'addon': 'fedora',
            'kind': 'folder',
            'name': '/ (Full Fedora)',
            'urls': {
                'folders': node.api_url_for('fedora_folder_list', folderId='/'),
            }
        }]

    client = DropboxClient(node_addon.external_account.oauth_key)
    file_not_found = HTTPError(http.NOT_FOUND, data=dict(message_short='File not found',
                                                  message_long='The Dropbox file '
                                                  'you requested could not be found.'))

    max_retry_error = HTTPError(http.REQUEST_TIMEOUT, data=dict(message_short='Request Timeout',
                                                   message_long='Dropbox could not be reached '
                                                   'at this time.'))

    try:
        metadata = client.metadata(folder_id)
    except ErrorResponse:
        raise file_not_found
    except MaxRetryError:
        raise max_retry_error

    # Raise error if folder was deleted
    if metadata.get('is_deleted'):
        raise file_not_found

    return [
        {
            'addon': 'fedora',
            'kind': 'folder',
            'id': item['path'],
            'name': item['path'].split('/')[-1],
            'path': item['path'],
            'urls': {
                'folders': node.api_url_for('fedora_folder_list', folderId=item['path']),
            }
        }
        for item in metadata['contents']
        if item['is_dir']
    ]

fedora_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

fedora_get_config = generic_views.get_config(
    SHORT_NAME,
    FedoraSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

fedora_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FedoraSerializer,
    _set_folder
)

fedora_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

fedora_root_folder = generic_views.root_folder(
    SHORT_NAME
)
