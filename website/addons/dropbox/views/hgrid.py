# -*- coding: utf-8 -*-
import os
import logging

from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.util import rubeus, api_url_for

from website.addons.dropbox.client import get_node_client

logger = logging.getLogger(__name__)
debug = logger.debug


def clean_path(path):
    """Ensure a path is formatted correctly for url_for."""
    return path.strip('/')

@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_hgrid_data_contents(**kwargs):
    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']
    path = kwargs.get('path', node_settings.folder)
    if not path.endswith('/'):  # ensure trailing slash
        path += '/'

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    client = get_node_client(node)
    files = []
    for item in client.metadata(path)['contents']:
        # TODO(sloria): Add a serialization function for a single item
        serialized = {}
        serialized['addon'] = 'dropbox'
        serialized['permissions'] = {
            'edit': can_edit,
            'view': can_view
        }
        serialized['name'] = os.path.basename(item['path'])
        serialized['ext'] = os.path.splitext(item['path'])[1]
        serialized[rubeus.KIND] = rubeus.FOLDER if item['is_dir'] else rubeus.FILE
        serialized['urls'] = build_dropbox_urls(item, node.api_url, node)
        files.append(serialized)

    return files


def dropbox_addon_folder(node_settings, auth, **kwargs):
    node = node_settings.owner
    return [
        rubeus.build_addon_root(
            node_settings=node_settings,
            name=node_settings.folder,
            permissions=auth,
            nodeUrl=node.url,
            nodeApiUrl=node.api_url,
        )
    ]


#TODO Fix to work with components
def build_dropbox_urls(item, api_url, node):
    path = clean_path(item['path'])  # Strip trailing and leading slashes
    if item['is_dir']:
        return {
            'upload': node.api_url_for('dropbox_upload', path=path),
            'fetch':  node.api_url_for('dropbox_hgrid_data_contents', path=path)
        }
    else:
        return {
            'download': node.web_url_for('dropbox_download', path=path),
            'view': node.web_url_for('dropbox_view_file', path=path),
            'delete': node.api_url_for('dropbox_delete_file', path=path)
        }
