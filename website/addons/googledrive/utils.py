# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive add-on.
"""
import os
import logging
from urllib import quote

logger = logging.getLogger(__name__)


class GoogleDriveNodeLogger(object):
    """Helper class for adding correctly-formatted Google Drive logs to nodes.

    Usage: ::

        from website.project.model import NodeLog

        node = ...
        auth = ...
        nodelogger = GoogleDriveNodeLogger(node, auth)
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
        relevant parameters and prefixing log events with `"googledrive_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder': self.node.get_addon('googledrive', deleted=True).folder_path
        }
        if extra:
            params.update(extra)
        # Prefix the action with googledrive
        self.node.add_log(
            action="googledrive_{0}".format(action),
            params=params,
            auth=self.auth
        )
        if save:
            self.node.save()


def build_googledrive_urls(item, node, path):
    return {
        'fetch': node.api_url_for('googledrive_folders', folderId=item['id']),
        'folders': node.api_url_for('googledrive_folders', folderId=item['id'], path=path),
    }


def to_hgrid(item, node, path):
    """
    :param item: contents returned from Google Drive API
    :return: results formatted as required for Hgrid display
    """
    # quote fails on unicode objects with unicode characters
    # covert to str with .encode('utf-8')
    safe_name = quote(item['title'].encode('utf-8'), safe='')
    path = os.path.join(path, safe_name)

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': safe_name,
        'addon': 'googledrive',
        'urls': build_googledrive_urls(item, node, path=path)
    }
    return serialized
