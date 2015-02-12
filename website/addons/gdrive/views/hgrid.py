
import httplib2
from flask import request

from website.project.model import Node
from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public, must_have_addon
from oauth2client.client import AccessTokenCredentials
from apiclient.discovery import build
from ..utils import to_hgrid, clean_path
from apiclient import errors

@must_be_contributor_or_public
@must_have_addon('gdrive', 'node')
def gdrive_folders(node_addon, **kwargs):

    node = node_addon.owner  # TODO change variable names
    nid = kwargs.get('nid') or kwargs.get('pid')
    node_addon = Node.load(nid)
    node_settings = node_addon.get_addon('gdrive')
    # Get service using Access token
    if node_settings:
        user_settings = node_settings.user_settings
        credentials = AccessTokenCredentials(user_settings.access_token, request.headers.get('User-Agent'))
        http_service = httplib2.Http()
        http_service = credentials.authorize(http_service)
        service = build('drive', 'v2', http_service)

    if request.args.get('foldersOnly'):
        folderid = request.args.get('folderId')
    path = request.args.get('path') or ''
    result = retrieve_all_files(service, folderid)
    contents = [to_hgrid(item, node, path=path)
                for item in result]
    return contents

def retrieve_all_files(service, folderId):
    """Retrieve a list of File resources.

    Args:
    service: Drive API service instance.
    Returns:
    List of File resources.
"""
    result = []
    page_token = None
    folderId = folderId or 'root'
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            if service:
                folders = service.files().list(q=" '%s' in parents and trashed = false and"
                                            " mimeType = 'application/vnd.google-apps.folder'" % folderId).execute()
                result.extend(folders['items'])
            page_token = folders.get('nextPageToken')
            if not page_token:
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
    path = {
        'path': clean_path(node_settings.folder['name']),
        'id': node_settings.folder['id']
    }
    # path = clean_path(node_settings.folder['name'])
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder['name'],
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
        path='/{0}/{1}/{2}'.format(path['id'], node_settings.folder['name'], path['path'].lstrip('/'))
    )
    return [root]
