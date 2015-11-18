# -*- coding: utf-8 -*-
import time
import logging
from datetime import datetime

# from OneDriveSDK
import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

from website.util import rubeus

from website.addons.onedrive import settings


logger = logging.getLogger(__name__)


class OnedriveNodeLogger(object):
    """Helper class for adding correctly-formatted Onedrive logs to nodes.

    Usage: ::

        from website.project.model import NodeLog

        node = ...
        auth = ...
        nodelogger = OnedriveNodeLogger(node, auth)
        nodelogger.log(NodeLog.FILE_REMOVED, save=True)


    :param Node node: The node to add logs to
    :param Auth auth: Authorization of the person who did the action.
    """
    def __init__(self, node, auth, path=None):
        self.node = node
        self.auth = auth
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"onedrive_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder_id': self.node.get_addon('onedrive', deleted=True).folder_id,
            # it used to be "folder": self.node.get_addon('onedrive', deleted=True).folder_name
            # changed to folder_path to make log show the complete folder path "/folder/subfolder"
            # instead of just showing the subfolder's name "/subfolder"
            'folder_name': self.node.get_addon('onedrive', deleted=True).folder_name,
            'folder': self.node.get_addon('onedrive', deleted=True).folder_path
        }
        # If logging a file-related action, add the file's view and download URLs
        if self.path:
            params.update({
                'urls': {
                    'view': self.node.web_url_for('addon_view_or_download_file', path=self.path, provider='onedrive'),
                    'download': self.node.web_url_for(
                        'addon_view_or_download_file',
                        path=self.path,
                        provider='onedrive'
                    )
                },
                'path': self.path,
            })
        if extra:
            params.update(extra)
        # Prefix the action with onedrive_
        self.node.add_log(
            action="onedrive_{0}".format(action),
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

        external_account.oauth_key = key['access_token']
        external_account.refresh_token = key['refresh_token']
        external_account.expires_at = datetime.utcfromtimestamp(time.time() + key['expires_in'])
        external_account.save()


def onedrive_addon_folder(node_settings, auth, **kwargs):
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
