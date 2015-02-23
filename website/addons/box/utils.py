# -*- coding: utf-8 -*-
import os
import logging

from website.util import rubeus

logger = logging.getLogger(__name__)


# TODO: Generalize this for other addons?
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


def get_file_name(path):
    """Given a path, get just the base filename.
    Handles "/foo/bar/baz.txt/" -> "baz.txt"
    """
    return os.path.basename(path.strip('/'))


def build_box_urls(item, node):
    assert item['type'] == 'folder', 'Can only build urls for box folders'
    # path = item['path']
    if item['type'] == u'folder':
        return {
            # Add extra endpoint for fetching folders only (used by node settings page)
            # NOTE: querystring params in camel-case
            'folders': node.api_url_for('box_hgrid_data_contents', foldersOnly=1, folder_id=item['id']),
        }


def metadata_to_hgrid(item, node, permissions):
    """Serializes a dictionary of metadata (returned from the BoxClient)
    to the format expected by Rubeus/HGrid.
    """
    filename = item['name']
    serialized = {
        'addon': 'box',
        'permissions': permissions,
        'name': filename,
        'ext': os.path.splitext(filename)[-1],
        rubeus.KIND: rubeus.FOLDER if item['type'] == u'folder' else rubeus.FILE,
        'urls': build_box_urls(item, node),
        'path': item.get('path') or filename,
        'id': item['id'],
    }
    return serialized
