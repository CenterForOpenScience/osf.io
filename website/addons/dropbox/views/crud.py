# -*- coding: utf-8 -*-
import logging
import httplib as http
import os


from website.project.utils import serialize_node, get_cache_content
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from website.addons.base.views import check_file_guid

from framework import request, redirect
from framework.exceptions import HTTPError

from website.addons.dropbox.model import DropboxFile

from ..client import get_node_addon_client

logger = logging.getLogger(__name__)
debug = logger.debug

@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_delete_file(path, auth, node_addon, **kwargs):
    if path and auth:
        client = get_node_addon_client(node_addon)
        return client.file_delete(path)
    raise HTTPError(http.BAD_REQUEST)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_upload(**kwargs):
    # Route may or may not have a path
    path = kwargs.get('path', '/')
    client = get_node_addon_client(kwargs.get('node_addon'))
    file_obj = request.files.get('file', None)
    if path and file_obj and client:
        path = os.path.join(path, file_obj.filename)
        return client.put_file(path, file_obj)  # TODO Cast to Hgrid
    raise HTTPError(http.BAD_REQUEST)


#TODO Force download start? maybe?
@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_download(path, node_addon, **kwargs):
    path = node_addon.folder
    version = kwargs.get('version', None)
    client = get_node_addon_client(node_addon)
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


def get_cache_file_name(file_obj):
    metadata = file_obj.get_metadata()
    return "{file}"

# TODO(sloria): TEST ME
def render_dropbox_file(client):
    pass




@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_view_file(path, node_addon, auth, **kwargs):
    if not path:
        raise HTTPError(http.NOT_FOUND)
    node = node_addon.owner
    client = get_node_addon_client(node_addon)
    # Lazily create a file GUID record
    file_obj, created = DropboxFile.get_or_create(node=node, path=path)

    redirect_url = check_file_guid(file_obj)
    if redirect_url:
        return redirect(redirect_url)


    download_url = node.web_url_for('dropbox_download', path=path)

    file_name = os.path.split(path)[1]
    response = {
        'file_name': file_name,
        'render_url': node.api_url_for('dropbox_render_file', path=path),
        'download_url': download_url,
        'rendered': 'TODO',
    }
    response.update(serialize_node(node, auth, primary=True))
    return response

##### MFR Rendering #####

@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_render_file(path, node_addon, auth, **kwargs):
    # TODO(sloria)
    return 'rendered html'

