
import httplib2
from flask import request

from website.project.model import Node
from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public, must_have_addon
from oauth2client.client import  AccessTokenCredentials
from apiclient.discovery import build
from ..utils import to_hgrid,clean_path
from apiclient import errors





#
# @must_be_contributor_or_public
# @must_have_addon('gdrive', 'node')
# def gdrive_hgrid_data_contents(node_addon, auth, **kwargs):
#     """Return the Rubeus/HGrid-formatted response for a folder's contents.
#
#     Takes optional query parameters `foldersOnly` (only return folders) and
#     `includeRoot` (include the root folder).
#     """
#     # No folder, just return an empty list of data
#     if node_addon.folder is None and not request.args.get('foldersOnly'):
#         return {'data': []}
#     node = node_addon.owner
#     path = kwargs.get('path', '')
#     # # Verify that path is a subdirectory of the node's shared folder
#     # if not is_authorizer(auth, node_addon):
#     #     abort_if_not_subdir(path, node_addon.folder)
#     # permissions = {
#     #     'edit': node.can_edit(auth) and not node.is_registration,
#     #     'view': node.can_view(auth)
#     # }
#     # client = get_node_client(node)
#     # file_not_found = HTTPError(http.NOT_FOUND, data=dict(message_short='File not found',
#     #                                               message_long='The Dropbox file '
#     #                                               'you requested could not be found.'))
#     #
#     # max_retry_error = HTTPError(http.REQUEST_TIMEOUT, data=dict(message_short='Request Timeout',
#     #                                                message_long='Dropbox could not be reached '
#     #                                                'at this time.'))
#
#     # try:
#     #     metadata = client.metadata(path)
#     # except ErrorResponse:
#     #     raise file_not_found
#     # except MaxRetryError:
#     #     raise max_retry_error
#
#     # Raise error if folder was deleted
#     # if metadata.get('is_deleted'):
#     #     raise file_not_found
#     # contents = metadata['contents']
#     # if request.args.get('foldersOnly'):
#     #     contents = [metadata_to_hgrid(file_dict, node, permissions) for
#     #                 file_dict in contents if file_dict['is_dir']]
#     # else:
#     #     contents = [metadata_to_hgrid(file_dict, node, permissions) for
#     #                 file_dict in contents]
#     if request.args.get('includeRoot'):
#         root = {'kind': rubeus.FOLDER, 'path': '/', 'name': '/ (Full Dropbox)'}
#         contents = root
#     return contents


@must_be_contributor_or_public
@must_have_addon('gdrive', 'node')
def get_gdrive_children(node_addon, **kwargs):
   auth = kwargs['auth']
   user = auth.user
   node = node_addon.owner #TODO change variable names
   nid = kwargs.get('nid') or kwargs.get('pid')
   node_addon= Node.load(nid)
   node_settings = node_addon.get_addon('gdrive')
   if node_settings:
       user_settings = node_settings.user_settings
       credentials = AccessTokenCredentials(user_settings.access_token, request.headers.get('User-Agent'))
       http_service = httplib2.Http()
       http_service = credentials.authorize(http_service)
       service = build('drive', 'v2', http_service)
   folderid = request.args.get('folderId')
   path = request.args.get('path') or ''
   result = retrieve_all_files(service, folderid)
   contents= [to_hgrid(item, node, path=path)
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
        Folders = service.files().list(q= " '%s' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'" %folderId).execute()
        result.extend(Folders['items'])
        page_token = Folders.get('nextPageToken')
        if not page_token:
            break
    except errors.HttpError, error:
      break
  return result


def gdrive_addon_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only."""
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder:
        return None
    node = node_settings.owner
    path= clean_path(node_settings.folder['path'])
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder,
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url
    )
    return [root]
