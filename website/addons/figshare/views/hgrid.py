# -*- coding: utf-8 -*-

from flask import request

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus

from ..api import Figshare
from ..utils import article_to_hgrid, project_to_hgrid


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_hgrid_data_contents(node_addon, **kwargs):

    node = node_addon.owner
    folders_only = bool(request.args.get('foldersOnly'))
    fs_type = kwargs.get('type', node_addon.figshare_type)
    fs_id = kwargs.get('id', node_addon.figshare_id)

    connect = Figshare.from_settings(node_addon.user_settings)
    if fs_type in ['article', 'fileset']:
        out = article_to_hgrid(
            node, connect.article(node_addon, fs_id)['items'][0],
            expand=True, folders_only=folders_only
        )
    elif fs_type == 'project':
        out = project_to_hgrid(
            node, connect.project(node_addon, fs_id),
            folders_only=folders_only
        )
    else:
        out = []

    return out if isinstance(out, list) else [out]


def figshare_hgrid_data(node_settings, auth, parent=None, **kwargs):
    node = node_settings.owner
    if node_settings.figshare_type == 'project':
        item = Figshare.from_settings(node_settings.user_settings).project(node_settings, node_settings.figshare_id)
    else:
        item = Figshare.from_settings(node_settings.user_settings).article(node_settings, node_settings.figshare_id)
    if not node_settings.figshare_id or not node_settings.has_auth or not item:
        return
    #TODO Test me
    #Throw error if neither
    node_settings.figshare_title = item.get('title') or item['items'][0]['title']
    node_settings.save()
    return [
        rubeus.build_addon_root(
            node_settings, u'{0}:{1}'.format(node_settings.figshare_title or 'Unnamed', node_settings.figshare_id), permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
        )
    ]


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_dummy_folder(node_settings, auth, parent=None, **kwargs):
    node_settings = kwargs.get('node_addon')
    auth = kwargs.get('auth')
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')  # noqa
    return figshare_hgrid_data(node_settings, auth, None, contents=False, **data)


#TODO Finish me
def figshare_hgrid_urls(node):
    node_settings = node.get_addon('figshare')
    connect = Figshare.from_settings(node_settings.user_settings)

    rv = project_to_hgrid(node, connect.project(node_settings, node_settings.figshare_id))

    rv = [n['urls']['view'] for n in rv]

    return rv
