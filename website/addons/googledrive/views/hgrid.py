# -*- coding: utf-8 -*-

from flask import request

from framework.exceptions import HTTPError

from website.util import rubeus
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_addon_authorizer

from website.addons.googledrive import exceptions
from website.addons.googledrive.utils import to_hgrid
from website.addons.googledrive.client import GoogleDriveClient


@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_be_addon_authorizer('googledrive')
def googledrive_folders(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed """
    node = kwargs.get('node') or kwargs['project']

    path = request.args.get('path', '')
    folder_id = request.args.get('folderId', 'root')

    try:
        access_token = user_addon.fetch_access_token()
    except exceptions.ExpiredAuthError:
        raise HTTPError(403)

    client = GoogleDriveClient(access_token)

    if folder_id == 'root':
        about = client.about()

        return [{
            'path': '/',
            'kind': rubeus.FOLDER,
            'id': about['rootFolderId'],
            'name': '/ (Full Google Drive)',
            'urls': {
                'get_folders': node.api_url_for('googledrive_folders', folderId=about['rootFolderId'])
            }
        }]

    contents = [
        to_hgrid(item, node, path=path)
        for item in client.folders(folder_id)
    ]

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
