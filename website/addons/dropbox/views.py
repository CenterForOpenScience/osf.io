"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
import logging

import httplib as http
from flask import request
from dropbox.rest import ErrorResponse
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon,
    must_be_contributor_or_public
)
from website.util import rubeus

from website.addons.dropbox import utils
from website.addons.dropbox.serializer import DropboxSerializer
from website.addons.base import generic_views

logger = logging.getLogger(__name__)
debug = logger.debug

SHORT_NAME = 'dropbox'
FULL_NAME = 'Dropbox'

dropbox_account_list = generic_views.account_list(
    SHORT_NAME,
    DropboxSerializer
)

dropbox_import_auth = generic_views.import_auth(
    SHORT_NAME,
    DropboxSerializer
)

def _get_folders(node_settings, folder_id):
    client = utils.get_client(node_settings.external_account)
    return utils.get_folders(client)

dropbox_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

dropbox_get_config = generic_views.get_config(
    SHORT_NAME,
    DropboxSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

dropbox_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    _set_folder
)

dropbox_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

dropbox_root_folder = generic_views.root_folder(
    SHORT_NAME
)

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

    client = utils.get_client(node_addon.external_account)
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
