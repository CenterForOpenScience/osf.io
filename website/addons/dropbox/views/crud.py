from dropbox.client import DropboxClient
import httplib as http

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public

from framework import request, redirect, Q
from framework.exceptions import HTTPError

from ..client import get_node_addon_client

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
    path = kwargs.get('path', None)
    with kwargs['dropbox'] as client:
        file = request.files.get('file', None)
        if path and file and client:
            return client.put(path, file)  # TODO Cast to Hgrid
    raise HTTPError(http.BAD_REQUEST)


#TODO Force download start? maybe?
@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_download(**kwargs):
    path = kwargs.get('path', None)
    version = kwargs.get('version', None)
    client = get_node_addon_client(kwargs['node_addon'])
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


def dropbox_render_file(**kwargs):
    pass
