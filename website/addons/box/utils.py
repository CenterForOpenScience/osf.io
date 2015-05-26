# -*- coding: utf-8 -*-
import time
import httplib
import logging
from datetime import datetime

from box import refresh_v2_token

from framework.exceptions import HTTPError

from website.util import rubeus

from website.addons.box import settings
from website.addons.box.serializer import BoxSerializer


logger = logging.getLogger(__name__)


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
            # it used to be "folder": self.node.get_addon('box', deleted=True).folder_name
            # changed to folder_path to make log show the complete folder path "/folder/subfolder"
            # instead of just showing the subfolder's name "/subfolder"
            'folder_name': self.node.get_addon('box', deleted=True).folder_name,
            'folder': self.node.get_addon('box', deleted=True).folder_path
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


def refresh_oauth_key(external_account, force=False):
    """If necessary, refreshes the oauth key associated with
    the external account.
    """
    if external_account.expires_at is None and not force:
        return

    if force or (external_account.expires_at - datetime.utcnow()).total_seconds() < settings.REFRESH_TIME:
        key = refresh_v2_token(settings.BOX_KEY, settings.BOX_SECRET, external_account.refresh_token)

        external_account.oauth_key = key['access_token']
        external_account.refresh_token = key['refresh_token']
        external_account.expires_at = datetime.utcfromtimestamp(time.time() + key['expires_in'])
        external_account.save()


def get_folders(client):
    """Gets a list of folders in a user's Box, including the root.
    Each folder is represented as a dict with its display name and path.
    """
    metadata = client.metadata('/', list=True)
    serializer = BoxSerializer
    # List each folder, including the root
    root = {
        'name': '/ (Full Box)',
        'path': '',
    }
    folders = [root] + [
        serializer.serialize_folder(each)
        for each in metadata['contents'] if each['is_dir']
    ]
    return folders


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
