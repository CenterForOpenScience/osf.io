# -*- coding: utf-8 -*-

import httplib as http

from flask import request
from dropbox.rest import ErrorResponse
from urllib3.exceptions import MaxRetryError

from framework.exceptions import HTTPError
from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.util import rubeus

from website.addons.dropbox.client import get_node_client
from website.addons.dropbox.utils import (
    metadata_to_hgrid,
    abort_if_not_subdir,
    is_authorizer,
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
    if not is_authorizer(auth, node_addon):
        abort_if_not_subdir(path, node_addon.folder)

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
        metadata_to_hgrid(file_dict, node, permissions) for
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
