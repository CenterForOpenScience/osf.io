"""Views fo the node settings page."""
# -*- coding: utf-8 -*-
from flask import request
import logging

from website.addons.dropbox.serializer import DropboxSerializer
from website.addons.base import generic_views
from website.project.decorators import must_have_addon, must_be_addon_authorizer

logger = logging.getLogger(__name__)
debug = logger.debug

SHORT_NAME = 'dropbox'
FULL_NAME = 'Dropbox'

dropbox_account_list = generic_views.account_list(
    SHORT_NAME,
    DropboxSerializer
)

dropbox_import_auth = generic_views.import_auth(
    SHORT_NAME,
    DropboxSerializer
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def dropbox_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    folder_id = request.args.get('folder_id')

    return node_addon.get_folders(folder_id=folder_id)

dropbox_get_config = generic_views.get_config(
    SHORT_NAME,
    DropboxSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

dropbox_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    DropboxSerializer,
    _set_folder
)

dropbox_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

dropbox_root_folder = generic_views.root_folder(
    SHORT_NAME
)
