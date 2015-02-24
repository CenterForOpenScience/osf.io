# -*- coding: utf-8 -*-

import httplib2

from flask import request
from apiclient.discovery import build
from oauth2client.client import AccessTokenCredentials

from website.util import rubeus
from website.util import permissions
from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_not_be_registration,
    must_be_addon_authorizer,
)

from website.addons.googledrive.utils import to_hgrid
from website.addons.googledrive.utils import check_access_token


@must_not_be_registration
@must_have_addon('googledrive', 'user')
@must_have_addon('googledrive', 'node')
@must_have_permission(permissions.WRITE)
@must_be_addon_authorizer('googledrive')
def googledrive_folders(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed """
    node = kwargs.get('node') or kwargs['project']

    # Get service using Access token
    user_settings = node_addon.user_settings
    check_access_token(user_settings)

    # Get service using oauth client
    http_service = httplib2.Http()
    # Why is user agent used here?
    credentials = AccessTokenCredentials(user_settings.access_token, request.headers.get('User-Agent'))
    http_service = credentials.authorize(http_service)
    service = build('drive', 'v2', http_service)

    path = request.args.get('path', '')
    folder_id = request.args.get('folderId')
    result = get_folders(service, folder_id=folder_id)
    contents = [
        to_hgrid(item, node, path=path)
        for item in result
    ]

    if request.args.get('includeRoot'):
        about = service.about().get().execute()
        root = {
            'kind': rubeus.FOLDER,
            'id': about['rootFolderId'],
            'name': '/ (Full Google Drive)',
            'path': '/',
        }
        contents.insert(0, root)
    return contents


def get_folders(service, folder_id=None):
    """Retrieve a list of File resources.

    :service: Drive API service instance.
    :return: List of File resources.
    """
    folderId = folder_id or 'root'
    query = ' and '.join([
        "'{0}' in parents".format(folderId),
        'trashed = false',
        "mimeType = 'application/vnd.google-apps.folder'",
    ])
    folders = service.files().list(q=query).execute()
    return folders['items']


def googledrive_addon_folder(node_settings, auth, **kwargs):
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
