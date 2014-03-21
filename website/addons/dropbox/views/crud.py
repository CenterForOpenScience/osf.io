# -*- coding: utf-8 -*-
import logging
import httplib as http
import os

from dropbox.client import DropboxClient

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from framework import request, redirect, Q
from framework.exceptions import HTTPError

from ..client import get_node_addon_client

logger = logging.getLogger(__name__)

@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_delete_file(**kwargs):
    auth = kwargs.get('auth', None)
    path = kwargs.get('path', None)
    if path and auth:
        user_setttings = auth.user.get_addon('dropbox')
        client = DropboxClient(user_setttings.access_token)
        return client.file_delete(path)
    raise HTTPError(http.BAD_REQUEST)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_upload(**kwargs):
    path = kwargs.get('path', '/')
    client = get_node_addon_client(kwargs['node_addon'])
    file_obj = request.files.get('file', None)
    if path and file_obj and client:
        path = os.path.join(path, file_obj.filename)
        return client.put_file(path, file_obj)  # TODO Cast to Hgrid
    raise HTTPError(http.BAD_REQUEST)


#TODO Force download start? maybe?
@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_download(**kwargs):
    node_settings = kwargs['node_addon']
    path = node_settings.folder
    version = kwargs.get('version', None)
    client = get_node_addon_client(node_settings)
    if path:
        if not version:
            return redirect(client.share(path)['url'])
        else:
            pass  # TODO
    raise HTTPError(http.BAD_REQUEST)


def dropbox_create_folder(**kwargs):
    pass


def dropbox_move_file(**kwargs):
    pass


def dropbox_get_versions(**kwargs):
    pass


def dropbox_view_file(**kwargs):
    pass
