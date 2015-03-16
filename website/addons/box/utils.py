# -*- coding: utf-8 -*-
import httplib
import logging

from framework.exceptions import HTTPError

from website.util import rubeus, web_url_for

from box.client import BoxClientException


logger = logging.getLogger(__name__)

BOX_SHARE_URL_TEMPLATE = 'https://app.box.com/files/0/f/{0}'


def serialize_folder(metadata):
    """Serializes metadata to a dict with the display name and path
    of the folder.
    """
    # if path is root
    if metadata['path'] == '' or metadata['path'] == '/':
        name = '/ (Full Box)'
    else:
        name = 'Box' + metadata['path']
    return {
        'name': name,
        'path': metadata['path'],
    }


def get_folders(client):
    """Gets a list of folders in a user's Box, including the root.
    Each folder is represented as a dict with its display name and path.
    """
    metadata = client.metadata('/', list=True)
    # List each folder, including the root
    root = {
        'name': '/ (Full Box)',
        'path': '',
    }
    folders = [root] + [
        serialize_folder(each)
        for each in metadata['contents'] if each['is_dir']
    ]
    return folders


def serialize_urls(node_settings):
    node = node_settings.owner

    urls = {
        'settings': web_url_for('user_addons'),
        'auth': node.api_url_for('box_oauth_start'),
        'config': node.api_url_for('box_config_put'),
        'files': node.web_url_for('collect_file_trees'),
        'emails': node.api_url_for('box_get_share_emails'),
        'share': BOX_SHARE_URL_TEMPLATE.format(node_settings.folder_id),
        'deauthorize': node.api_url_for('box_deauthorize'),
        'importAuth': node.api_url_for('box_import_user_auth'),
        # Endpoint for fetching only folders (including root)
        'folders': node.api_url_for('box_list_folders'),
    }
    return urls


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    BoxNodeSettings record. Provides the return value for the
    box config endpoints.
    """
    valid_credentials = True
    user_settings = node_settings.user_settings
    current_user_settings = current_user.get_addon('box')
    user_is_owner = user_settings is not None and user_settings.owner == current_user

    if user_settings:
        try:
            client = client or user_settings.oauth_settings.get_client
            client.get_user_info()
        except BoxClientException:
            valid_credentials = False

    result = {
        'userIsOwner': user_is_owner,
        'nodeHasAuth': node_settings.has_auth,
        'urls': serialize_urls(node_settings),
        'validCredentials': valid_credentials,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
    }

    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for(
            'profile_view_id',
            uid=user_settings.owner._id
        )
        result['ownerName'] = user_settings.owner.fullname
        # Show available folders
        # path = node_settings.folder

        if node_settings.folder_id is None:
            result['folder'] = {'name': None, 'path': None}
        elif valid_credentials:
            path = node_settings.fetch_full_folder_path()

            result['folder'] = {
                'path': path,
                'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full Box)'
            }
    return result


class BoxNodeLogger(object):
    """Helper class for adding correctly-formatted Box logs to nodes.

    Usage: ::

        from website.project.model import NodeLog

        file_obj = BoxFile(path='foo/bar.txt')
        file_obj.save()
        node = ...
        auth = ...
        nodelogger = BoxNodeLogger(node, auth, file_obj)
        nodelogger.log(NodeLog.FILE_REMOVED, save=True)


    :param Node node: The node to add logs to
    :param Auth auth: Authorization of the person who did the action.
    :param BoxFile file_obj: File object for file-related logs.
    """
    def __init__(self, node, auth, file_obj=None, path=None):
        self.node = node
        self.auth = auth
        self.file_obj = file_obj
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"box_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder_id': self.node.get_addon('box', deleted=True).folder_id,
        }
        # If logging a file-related action, add the file's view and download URLs
        if self.file_obj or self.path:
            path = self.file_obj.path if self.file_obj else self.path
            params.update({
                'urls': {
                    'view': self.node.web_url_for('addon_view_or_download_file', path=path, provider='box'),
                    'download': self.node.web_url_for(
                        'addon_view_or_download_file',
                        path=path,
                        provider='box'
                    )
                },
                'path': path,
            })
        if extra:
            params.update(extra)
        # Prefix the action with box_
        self.node.add_log(
            action="box_{0}".format(action),
            params=params,
            auth=self.auth
        )
        if save:
            self.node.save()


def handle_box_error(error, msg):
    if (error is 'invalid_request' or 'unsupported_response_type'):
        raise HTTPError(httplib.BAD_REQUEST)
    if (error is 'access_denied'):
        raise HTTPError(httplib.FORBIDDEN)
    if (error is 'server_error'):
        raise HTTPError(httplib.INTERNAL_SERVER_ERROR)
    if (error is 'temporarily_unavailable'):
        raise HTTPError(httplib.SERVICE_UNAVAILABLE)
    raise HTTPError(httplib.INTERNAL_SERVER_ERROR)


def box_addon_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only."""
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder_id:
        return None

    node = node_settings.owner

    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.fetch_folder_name(),
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )

    return [root]
