# -*- coding: utf-8 -*-
from flask import request

from website.project.decorators import must_have_addon, must_be_addon_authorizer

from addons.base import generic_views
from addons.googledriveinstitutions.serializer import GoogleDriveInstitutionsSerializer

SHORT_NAME = 'googledriveinstitutions'
FULL_NAME = 'Google Drive in G Suite / Google Workspace'

googledriveinstitutions_account_list = generic_views.account_list(
    SHORT_NAME,
    GoogleDriveInstitutionsSerializer
)

googledriveinstitutions_get_config = generic_views.get_config(
    SHORT_NAME,
    GoogleDriveInstitutionsSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

googledriveinstitutions_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    GoogleDriveInstitutionsSerializer,
    _set_folder
)

googledriveinstitutions_import_auth = generic_views.import_auth(
    SHORT_NAME,
    GoogleDriveInstitutionsSerializer
)

googledriveinstitutions_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def googledriveinstitutions_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path', '')
    folder_id = request.args.get('folder_id', 'root')

    return node_addon.get_folders(folder_path=path, folder_id=folder_id)
