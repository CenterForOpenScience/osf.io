# -*- coding: utf-8 -*-

from flask import request

from framework.auth.decorators import must_be_logged_in

from website.util import rubeus
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public

from ..api import Figshare
from ..utils import article_to_hgrid, project_to_hgrid


@must_be_logged_in
@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_hgrid_data_contents(node_addon, auth, **kwargs):

    node = node_addon.owner
    folders_only = bool(request.args.get('foldersOnly'))
    fs_type = kwargs.get('type', node_addon.figshare_type)
    fs_id = kwargs.get('id', node_addon.figshare_id)

    connect = Figshare.from_settings(node_addon.user_settings)
    if fs_type in ['article', 'fileset']:
        out = article_to_hgrid(
            node, auth.user,
            connect.article(node_addon, fs_id)['items'][0],
            expand=True, folders_only=folders_only
        )
    elif fs_type == 'project':
        out = project_to_hgrid(
            node=node,
            project=connect.project(node_addon, fs_id),
            user=auth.user,
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
def figshare_dummy_folder(node_addon, auth, parent=None, **kwargs):
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')  # noqa
    return figshare_hgrid_data(node_addon, auth, None, contents=False, **data)
