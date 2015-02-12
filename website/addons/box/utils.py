# -*- coding: utf-8 -*-
import os
import logging
import httplib as http
from datetime import datetime

from flask import make_response
from boxview.boxview import BoxViewError

from framework.exceptions import HTTPError
from website.project.utils import get_cache_content
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
            'folder': self.node.get_addon('box', deleted=True).folder
        }
        # If logging a file-related action, add the file's view and download URLs
        if self.file_obj or self.path:
            path = self.file_obj.path if self.file_obj else self.path
            cleaned_path = clean_path(path)
            params.update({
                'urls': {
                    'view': self.node.web_url_for('box_view_file', path=cleaned_path),
                    'download': self.node.web_url_for(
                        'box_download', path=cleaned_path)
                },
                'path': cleaned_path,
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


def is_subdir(path, directory):
    if not (path and directory):
        return False
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
    return path.strip('/')


def make_file_response(fileobject, metadata):
    """Builds a response from a file-like object and metadata returned by
    a Box client.
    """
    resp = make_response(fileobject.read())
    filename = get_file_name(metadata['path'])
    rev = metadata.get('rev')
    if rev:
        # add revision to filename
        # foo.mp3 -> foo-abc123.mp3
        filename = '-{rev}'.format(rev=rev).join(os.path.splitext(filename))
    disposition = 'attachment; filename={0}'.format(filename)
    resp.headers['Content-Disposition'] = disposition
    resp.headers['Content-Type'] = metadata.get('mime_type', 'application/octet-stream')
    return resp


def ensure_leading_slash(path):
    if not path.startswith('/'):
        return '/' + path
    return path


def build_box_urls(item, node):
    path = clean_path(item['path'])  # Strip trailing and leading slashes
    if item['type']==u'folder':
        return {
            'upload': node.api_url_for('box_upload', path=path),
            # Endpoint for fetching all of a folder's contents
            'fetch': node.api_url_for('box_hgrid_data_contents', path=path),
            # Add extra endpoint for fetching folders only (used by node settings page)
            # NOTE: querystring params in camel-case
            'folders': node.api_url_for('box_hgrid_data_contents',
                path=path, foldersOnly=1)
        }
    else:
        return {
            'download': node.web_url_for('box_download', path=path),
            'view': node.web_url_for('box_view_file', path=path),
            'delete': node.api_url_for('box_delete_file', path=path)
        }


def metadata_to_hgrid(item, node, permissions):
    """Serializes a dictionary of metadata (returned from the BoxClient)
    to the format expected by Rubeus/HGrid.
    """
    #import ipdb; ipdb.set_trace()
    filename = item['name']  # get_file_name(item['path'])
    serialized = {
        'addon': 'box',
        'permissions': permissions,
        'name': item['name'],
        'ext': os.path.splitext(filename)[-1],
        rubeus.KIND: rubeus.FOLDER if item['type']==u'folder' else rubeus.FILE,
        #'urls': build_box_urls(item, node),
        'path': item['name'],
        'id': item['id']
    }
    return serialized


def get_share_folder_uri(path):
    """Return the URI for sharing a folder through the box interface.
    This is not exposed through Box's REST API, so need to build the URI
    "manually".
    """
    cleaned = clean_path(path)
    return ('https://box.com/home/{cleaned}'
            '?shareoptions=1&share_subfolder=0&share=1').format(cleaned=cleaned)


def refresh_creds_if_necessary(user_settings):
    """Checks to see if the access token has expired, or will 
    expire within 6 minutes. Returns the status of a refresh 
    attempt or True if not required.
    """   
    #import ipdb; ipdb.set_trace()
    diff = (datetime.utcnow() - user_settings.last_refreshed).total_seconds() / 3600
    if diff > 0.9:
        return user_settings.get_credentialsv2().refresh()
    else:
        return True
