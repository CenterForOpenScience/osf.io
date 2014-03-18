from website.project.decorators import must_be_contributor_or_public, must_have_addon
from framework import request
from urllib import unquote
from website.util import rubeus
from framework.exceptions import HTTPError
import httplib as http


def dropbox_hgrid_data(node_settings, auth, **kwargs):

    node = node_settings.owner
    return [
        rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
        )
    ]


@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_hgrid_data_contents(**kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']
    path = unquote(kwargs.get('path', None)) + '/' if kwargs.get('path', None) else None

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    #Assuming client is a dropbox client
    client = "Todo"
    files = []

    for item in client.metadata('/')['contents']:

        temp_file = []
        temp_file['addon'] = 'dropbox'
        temp_file['permissions'] = {
            'edit': can_edit,
            'view': can_view
        }
        temp_file['name'] = item['path']  #TODO might need to be split
        #Name Size Ext URLS

        #Folder
        files.append(temp_file)

    return files


@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_addon_folder(**kwargs):
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()
    return dropbox_hgrid_data(node_settings, auth, **data)
