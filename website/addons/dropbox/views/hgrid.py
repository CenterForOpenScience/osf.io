# -*- coding: utf-8 -*-
import os
import logging

from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.util import rubeus, api_url_for

from website.addons.dropbox.client import get_node_client

logger = logging.getLogger(__name__)
debug = logger.debug


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
        serialized['urls'] = build_dropbox_urls(item, node.api_url, node._id)
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
#TODO Fix settings naming conflict
def build_dropbox_urls(item, api_url, nid):
    if item['is_dir']:
        return {
            'upload': api_url_for('dropbox_upload', path=item['path'], pid=nid),
            'fetch':  api_url_for('dropbox_hgrid_data_contents', path=item['path'], pid=nid)
        }
    else:
        return {
            'download': api_url_for('dropbox_download', path=item['path'], pid=nid),
            'view': '/{0}/dropbox{1}/'.format(nid, item['path']), #TODO Write me
            'delete': api_url_for('dropbox_download', path=item['path'], pid=nid)
        }
