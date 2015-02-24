# -*- coding: utf-8 -*-

import httplib2

from flask import request
from apiclient import errors
from apiclient.discovery import build
from oauth2client.client import AccessTokenCredentials

from website.util import rubeus
from website.project.model import Node
from website.project.decorators import must_be_contributor_or_public, must_have_addon

from ..utils import to_hgrid, check_access_token


@must_be_contributor_or_public
@must_have_addon('gdrive', 'node')
def gdrive_folders(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed """
    node_owner = node_addon.owner
    nid = kwargs.get('nid') or kwargs.get('pid')
    node = Node.load(nid)
    node_settings = node.get_addon('gdrive')

    # Get service using Access token
    if node_settings:
        user_settings = node_settings.user_settings
        check_access_token(user_settings)
        # Get service using oauth client
        http_service = httplib2.Http()
        credentials = AccessTokenCredentials(user_settings.access_token, request.headers.get('User-Agent'))
        http_service = credentials.authorize(http_service)
        service = build('drive', 'v2', http_service)

    path = request.args.get('path') or ''
    folderid = request.args.get('folderId')
    if request.args.get('foldersOnly'):
        result = retrieve_all_files(service, folderid=folderid, foldersonly=1)
    else:
        result = retrieve_all_files(service, folderid=folderid, foldersonly=0)
    contents = [
        to_hgrid(item, node_owner, path=path)
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


def retrieve_all_files(service, folderid=None, foldersonly=0):
    """Retrieve a list of File resources.

    :service: Drive API service instance.
    :return: List of File resources.
    """
    result = []
    folderId = folderid or 'root'
    while True:
        try:
            if service:
                if foldersonly:
                    folders = service.files().list(q=" '%s' in parents and trashed = false and "
                                                   "mimeType = 'application/vnd.google-apps.folder' "
                                                   % folderId).execute()
                else:
                    folders = service.files().list(q=" '%s' in parents and trashed = false" % folderId).execute()

                result.extend(folders['items'])
                break
        except errors.HttpError:
            break
    return result


def gdrive_addon_folder(node_settings, auth, **kwargs):
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
