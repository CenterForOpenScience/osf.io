# -*- coding: utf-8 -*-

from flask import request

from website.util import rubeus
from website.util import permissions
from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_not_be_registration,
    must_be_addon_authorizer,
)

from website.addons.googledrive.utils import to_hgrid
from website.addons.googledrive.client import GoogleDriveClient


@must_not_be_registration
@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_have_permission(permissions.WRITE)
@must_be_addon_authorizer('googledrive')
def googledrive_folders(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed """
    node = kwargs.get('node') or kwargs['project']

    path = request.args.get('path', '')
    folder_id = request.args.get('folderId', 'root')

    client = GoogleDriveClient(user_addon.access_token)
    contents = [
        to_hgrid(item, node, path=path)
        for item in client.folders(folder_id)
    ]

    if request.args.get('includeRoot'):
        about = client.about()
        root = {
            'kind': rubeus.FOLDER,
            'id': about['rootFolderId'],
            'name': '/ (Full Google Drive)',
            'path': '/',
        }
        contents.insert(0, root)
    return contents


def googledrive_addon_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only."""
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder_id:
        return None
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder_name,
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]
