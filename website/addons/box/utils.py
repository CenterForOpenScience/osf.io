# -*- coding: utf-8 -*-
import httplib
import logging

from framework.exceptions import HTTPError

from website.util import rubeus

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
    if not node_settings.has_auth:
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
