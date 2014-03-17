from dropbox.client import DropboxClient
import httplib as http

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from framework import request, redirect, Q
from framework.exceptions import HTTPError


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
    auth = kwargs.get('auth', None)
    path = kwargs.get('path', None)
    file = request.files.get('file', None)
    if path and auth and file:
        user_setttings = auth.user.get_addon('dropbox')
        client = DropboxClient(user_setttings.access_token)
        return client.put(path, file)  # TODO Cast to Hgrid
    raise HTTPError(http.BAD_REQUEST)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_download(**kwargs):
    path = kwargs.get('path', None)
    version = kwargs.get('version', None)
    auth = kwargs.get('auth', None)
    if path and auth:
        if not version:
            user_setttings = auth.user.get_addon('dropbox')
            client = DropboxClient(user_setttings.access_token)
            redirect(client.share(path)['url'])
        else:
            pass  # TODO
    raise HTTPError(http.BAD_REQUEST)

def dropbox_create_folder(**kwargs):
    pass


def dropbox_move_file(**kwargs):
    pass


def dropbox_get_versions(**kwargs):
    pass


def dropbox_render_file(**kwargs):
    pass
