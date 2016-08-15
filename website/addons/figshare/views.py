# -*- coding: utf-8 -*-

from website.addons.base import generic_views
from website.addons.figshare.serializer import FigshareSerializer
from website.addons.figshare.utils import options_to_hgrid

from website.util import rubeus

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
)

SHORT_NAME = 'figshare'
FULL_NAME = SHORT_NAME

figshare_account_list = generic_views.account_list(
    SHORT_NAME,
    FigshareSerializer
)

figshare_import_auth = generic_views.import_auth(
    SHORT_NAME,
    FigshareSerializer
)

figshare_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

figshare_get_config = generic_views.get_config(
    SHORT_NAME,
    FigshareSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

figshare_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FigshareSerializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def figshare_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    folders = node_addon.get_folders()
    return options_to_hgrid(node_addon.owner, folders) or []

def figshare_root_folder(node_settings, auth, **kwargs):
    if not node_settings.has_auth or not node_settings.folder_id:
        return None
    node = node_settings.owner
    if node_settings.figshare_type == 'project':
        item = node_settings.api.project(node_settings, node_settings.figshare_id)
    else:
        item = node_settings.api.article(node_settings, node_settings.figshare_id)

    return [
        rubeus.build_addon_root(
            node_settings=node_settings,
            name=node_settings.fetch_folder_name(),
            permissions=auth,
            nodeUrl=node.url,
            nodeApiUrl=node.api_url,
            extra={
                'status': (item.get('articles') or item['items'])[0]['status'].lower()
            },
            private_key=kwargs.get('view_only', None),
        )
    ]
