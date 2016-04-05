# -*- coding: utf-8 -*-
from flask import request

from framework.exceptions import HTTPError
from website.project.decorators import must_have_addon, must_be_addon_authorizer

from website.addons.base import generic_views
from website.addons.base.exceptions import InvalidAuthError

from website.addons.googledrive.utils import to_hgrid
from website.addons.googledrive.client import GoogleDriveClient
from website.addons.googledrive.serializer import GoogleDriveSerializer

SHORT_NAME = 'googledrive'
FULL_NAME = 'Google Drive'

googledrive_account_list = generic_views.account_list(
    SHORT_NAME,
    GoogleDriveSerializer
)

googledrive_get_config = generic_views.get_config(
    SHORT_NAME,
    GoogleDriveSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

googledrive_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    GoogleDriveSerializer,
    _set_folder
)

googledrive_import_auth = generic_views.import_auth(
    SHORT_NAME,
    GoogleDriveSerializer
)

googledrive_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

googledrive_root_folder = generic_views.root_folder(
    SHORT_NAME
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def googledrive_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    node = kwargs.get('node') or node_addon.owner

    path = request.args.get('path', '')
    folder_id = request.args.get('folderId', 'root')

    try:
        access_token = node_addon.fetch_access_token()
    except InvalidAuthError:
        raise HTTPError(403)

    client = GoogleDriveClient(access_token)

    if folder_id == 'root':
        about = client.about()

        return [{
            'path': '/',
            'kind': 'folder',
            'id': about['rootFolderId'],
            'name': '/ (Full Google Drive)',
            'urls': {
                'folders': node.api_url_for('googledrive_folder_list', folderId=about['rootFolderId'])
            }
        }]

    contents = [
        to_hgrid(item, node, path=path)
        for item in client.folders(folder_id)
    ]
    return contents
