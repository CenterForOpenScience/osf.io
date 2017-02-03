"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

import logging

from flask import request

from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
)

from website.addons.base import generic_views
from website.addons.onedrive.serializer import OneDriveSerializer

logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)

SHORT_NAME = 'onedrive'
FULL_NAME = 'Microsoft OneDrive'

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
    """Returns a list of folders in OneDrive"""
    if not node_addon.has_auth:
        raise HTTPError(http.FORBIDDEN)

    path = request.args.get('path', '')
    folder_id = request.args.get('folder_id', 'root')

    return node_addon.get_folders(folder_path=path, folder_id=folder_id)
