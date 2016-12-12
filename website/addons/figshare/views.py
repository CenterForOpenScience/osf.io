# -*- coding: utf-8 -*-

from website.addons.base import generic_views
from website.addons.figshare.serializer import FigshareSerializer

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
)

from website.util import rubeus


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
    node_addon.set_folder(folder['id'], auth=auth)
    node_addon.save()

figshare_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FigshareSerializer,
    _set_folder
)

def figshare_root_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only.

    Identical to the generic_views.root_folder except adds root_folder_type
    to exported data.  Fangorn needs root_folder_type to decide whether to
    display the 'Create Folder' button.
    """
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder_id:
        return None
    node = node_settings.owner
    return [rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.fetch_folder_name(),
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
        rootFolderType=node_settings.folder_path,
        private_key=kwargs.get('view_only', None),
    )]

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def figshare_folder_list(node_addon, **kwargs):
    """ Returns all linkable projects / articles at root.
    """
    return node_addon.get_folders()
