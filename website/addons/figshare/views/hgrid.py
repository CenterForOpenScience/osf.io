from mako.template import Template

from framework import request
from framework.auth import get_current_user

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus

from ..api import Figshare

@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_hgrid_data_contents(*args, **kwargs):
    
    node_settings = kwargs.get('node_addon')
    node = node_settings.owner
    figshare_settings = node.get_addon('figshare')
    auth = kwargs['auth']
    path = ''

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    connect = Figshare.from_settings(figshare_settings.user_settings)

    fs_type = kwargs.get('type')
    fs_id = kwargs.get('id')

    contents = False
    if fs_type and fs_id:
        contents = True

    if not fs_type:
        fs_type = figshare_settings.figshare_type
    if not fs_id:
        fs_id = figshare_settings.figshare_id

    hgrid_tree = connect.tree_to_hgrid(node, 
                                       node_settings, 
                                       fs_id, 
                                       fs_type, 
                                       contents)
    
    return hgrid_tree


def figshare_hgrid_data(node_settings, auth, parent=None, **kwargs):
    if not node_settings.figshare_id:
        return
    return [rubeus.build_addon_root(node_settings, node_settings.figshare_id, permissions=auth)]


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_dummy_folder(node_settings, auth, parent=None, **kwargs):
    if not node_settings.figshare_id:
       return

    node_settings = kwargs.get('node_addon')
    user = kwargs.get('auth').user
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')

    return figshare_hgrid_data(node_settings, user, None, contents=False, **data)


