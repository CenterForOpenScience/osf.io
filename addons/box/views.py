"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from flask import request

from addons.base import generic_views
from addons.box.serializer import BoxSerializer
from website.project.decorators import must_have_addon, must_be_addon_authorizer

SHORT_NAME = 'box'
FULL_NAME = 'Box'

box_account_list = generic_views.account_list(
    SHORT_NAME,
    BoxSerializer
)

box_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BoxSerializer
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def box_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    folder_id = request.args.get('folder_id')

    return node_addon.get_folders(folder_id=folder_id)

box_get_config = generic_views.get_config(
    SHORT_NAME,
    BoxSerializer
)

def _set_folder(node_addon, folder, auth):
    uid = folder['id']
    node_addon.set_folder(uid, auth=auth)
    node_addon.save()

box_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    BoxSerializer,
    _set_folder
)

box_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

box_root_folder = generic_views.root_folder(
    SHORT_NAME
)
