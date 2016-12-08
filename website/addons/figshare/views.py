# -*- coding: utf-8 -*-

from website.addons.base import generic_views
from website.addons.figshare.serializer import FigshareSerializer

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
    node_addon.set_folder(folder['id'], auth=auth)
    node_addon.save()

figshare_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FigshareSerializer,
    _set_folder
)

figshare_root_folder = generic_views.root_folder(
    SHORT_NAME
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def figshare_folder_list(node_addon, **kwargs):
    """ Returns all linkable projects / articles at root.
    """
    return node_addon.get_folders()
