import os

from website.project.decorators import must_be_contributor_or_public, must_have_addon
from urllib import unquote
from website.util import rubeus


from ..client import get_node_client


@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_hgrid_data_contents(**kwargs):
    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']
    path = kwargs.get('path', '') + '/'  # Might need to be unquoted

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    client = get_node_client(node)
    files = []
    for item in client.metadata(path)['contents']:

        temp_file = {}
        temp_file['addon'] = 'dropbox'
        temp_file['permissions'] = {
            'edit': can_edit,
            'view': can_view
        }
        temp_file['name'] = os.path.basename(item['path'])
        temp_file['ext'] = os.path.splitext(item['path'])[1]
        temp_file[rubeus.KIND] = rubeus.FOLDER if item['is_dir'] else rubeus.FILE
        temp_file['urls'] = build_dropbox_urls(item, node.api_url, node._id)

        files.append(temp_file)

    return files


def dropbox_addon_folder(node_settings, auth, **kwargs):
    node = node_settings.owner
    return [
        rubeus.build_addon_root(
            node_settings, node_settings.folder, permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
        )
    ]


def build_dropbox_urls(item, api_url, nid):
    if item['is_dir']:
        return {
            'upload': '{0}dropbox{1}'.format(api_url, item['path']),
            'fetch': '{0}dropbox/hgrid{1}'.format(api_url, item['path']),
        }
    else:
        return {
            'download': '{0}dropbox{1}/'.format(api_url, item['path']),
            'view': '/{0}/dropbox{1}/'.format(nid, item['path']),
            'delete': '{0}dropbox{1}/'.format(api_url, item['path']),
        }
