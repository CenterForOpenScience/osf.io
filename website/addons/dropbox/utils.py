# -*- coding: utf-8 -*-
import os
import logging
import httplib as http

from framework.exceptions import HTTPError
from website.util import rubeus

logger = logging.getLogger(__name__)


# TODO: Generalize this for other addons?
class DropboxNodeLogger(object):
    """Helper class for adding correctly-formatted Dropbox logs to nodes.

    Usage: ::

        from website.project.model import NodeLog

        file_obj = DropboxFile(path='foo/bar.txt')
        file_obj.save()
        node = ...
        auth = ...
        nodelogger = DropboxNodeLogger(node, auth, file_obj)
        nodelogger.log(NodeLog.FILE_REMOVED, save=True)


    :param Node node: The node to add logs to
    :param Auth auth: Authorization of the person who did the action.
    :param DropboxFile file_obj: File object for file-related logs.
    """
    def __init__(self, node, auth, file_obj=None, path=None):
        self.node = node
        self.auth = auth
        self.file_obj = file_obj
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"dropbox_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder': self.node.get_addon('dropbox', deleted=True).folder
        }
        if extra:
            params.update(extra)
        # Prefix the action with dropbox_
        self.node.add_log(
            action="dropbox_{0}".format(action),
            params=params,
            auth=self.auth
        )
        if save:
            self.node.save()


def is_subdir(path, directory):
    if not (path and directory):
        return False
    # directory is root directory
    if directory == '/':
        return True
    #make both absolute
    abs_directory = os.path.abspath(directory).lower()
    abs_path = os.path.abspath(path).lower()
    return os.path.commonprefix([abs_path, abs_directory]) == abs_directory


def is_authorizer(auth, node_addon):
    """Return if the auth object's user is the same as the authorizer of the node."""
    return auth.user == node_addon.user_settings.owner


def abort_if_not_subdir(path, directory):
    """Check if path is a subdirectory of directory. If not, abort the current
    request with a 403 error.
    """
    if not is_subdir(clean_path(path), clean_path(directory)):
        raise HTTPError(http.FORBIDDEN)
    return True


def get_file_name(path):
    """Given a path, get just the base filename.
    Handles "/foo/bar/baz.txt/" -> "baz.txt"
    """
    return os.path.basename(path.strip('/'))


def clean_path(path):
    """Ensure a path is formatted correctly for url_for."""
    if path is None:
        return ''
    if path == '/':
        return path
    return path.strip('/')


def ensure_leading_slash(path):
    if not path.startswith('/'):
        return '/' + path
    return path


def metadata_to_hgrid(item, node, permissions):
    """Serializes a dictionary of metadata (returned from the DropboxClient)
    to the format expected by Rubeus/HGrid.
    """
    filename = get_file_name(item['path'])
    serialized = {
        'addon': 'dropbox',
        'permissions': permissions,
        'name': get_file_name(item['path']),
        'ext': os.path.splitext(filename)[1],
        rubeus.KIND: rubeus.FOLDER if item['is_dir'] else rubeus.FILE,
        'path': item['path'],
        'urls': {
            'folders': node.api_url_for(
                'dropbox_hgrid_data_contents',
                path=clean_path(item['path']),
            ),
        }
    }
    return serialized


def get_share_folder_uri(path):
    """Return the URI for sharing a folder through the dropbox interface.
    This is not exposed through Dropbox's REST API, so need to build the URI
    "manually".
    """
    cleaned = clean_path(path)
    return ('https://dropbox.com/home/{cleaned}'
            '?shareoptions=1&share_subfolder=0&share=1').format(cleaned=cleaned)
