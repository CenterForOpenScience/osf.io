"""Views for the node settings page."""
# -*- coding: utf-8 -*-

from flask import request

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
)

from addons.base import generic_views
from addons.onedrive.serializer import OneDriveSerializer


SHORT_NAME = 'onedrive'
FULL_NAME = 'OneDrive'

onedrive_account_list = generic_views.account_list(
    SHORT_NAME,
    OneDriveSerializer
)

onedrive_get_config = generic_views.get_config(
    SHORT_NAME,
    OneDriveSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

onedrive_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    OneDriveSerializer,
    _set_folder
)

onedrive_import_auth = generic_views.import_auth(
    SHORT_NAME,
    OneDriveSerializer
)

onedrive_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def onedrive_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    folder_id = request.args.get('folder_id')
    return node_addon.get_folders(folder_id=folder_id)
