# -*- coding: utf-8 -*-
import logging
import httplib as http
import os

from modularodm import Q

from website.project.utils import serialize_node, get_cache_content
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from website.addons.base.views import check_file_guid

from framework import request, redirect
from framework.exceptions import HTTPError

from website.addons.dropbox.model import DropboxFile
from website.addons.dropbox.client import get_node_addon_client
from website.addons.dropbox.utils import (
    render_dropbox_file, get_file_name, metadata_to_hgrid
)

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
def dropbox_upload(node_addon, auth, **kwargs):
    # Route may or may not have a path
    path = kwargs.get('path', node_addon.folder)
    client = get_node_addon_client(node_addon)
    file_obj = request.files.get('file', None)
    node = node_addon.owner
    if path and file_obj and client:
        path = os.path.join(path, file_obj.filename)
        metadata = client.put_file(path, file_obj)  # TODO Cast to Hgrid
        permissions = {
            'edit': node.can_edit(auth),
            'view': node.can_view(auth)
        }
        return metadata_to_hgrid(metadata, node=node, permissions=permissions)
    raise HTTPError(http.BAD_REQUEST)


#TODO Force download start? maybe?
@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_download(path, node_addon, **kwargs):
    client = get_node_addon_client(node_addon)
    if path:
        return redirect(client.media(path)['url'])
    raise HTTPError(http.BAD_REQUEST)


def dropbox_create_folder(**kwargs):
    pass


def dropbox_move_file(**kwargs):
    pass


def dropbox_get_versions(**kwargs):
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
    rendered = render_dropbox_file(file_obj, client=client)
    revisions = client.revisions(path)
    response = {
        'revisions': revisions,
        'file_name': get_file_name(path),
        'render_url': node.api_url_for('dropbox_render_file', path=path.strip('/')),
        'download_url': file_obj.download_url,
        'rendered': rendered,
    }
    response.update(serialize_node(node, auth, primary=True))
    return response

##### MFR Rendering #####

@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_render_file(path, node_addon, auth, **kwargs):
    # TODO(sloria)
    file_obj = DropboxFile.find_one(Q('path', 'eq', path))
    client = get_node_addon_client(node_addon)
    filename = file_obj.get_cache_filename(client=client)
    return get_cache_content(node_addon, filename)
