# -*- coding: utf-8 -*-
import logging
import httplib as http
import os

from modularodm import Q

from website.project.model import NodeLog
from website.project.utils import serialize_node
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from website.addons.base.views import check_file_guid

from framework import request, redirect, make_response
from framework.exceptions import HTTPError

from website.addons.dropbox.model import DropboxFile
from website.addons.dropbox.client import get_node_addon_client
from website.addons.dropbox.utils import (
    render_dropbox_file, get_file_name, metadata_to_hgrid, clean_path,
    DropboxNodeLogger
)

logger = logging.getLogger(__name__)
debug = logger.debug


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_delete_file(path, auth, node_addon, **kwargs):
    node = node_addon.owner
    if path and auth:
        client = get_node_addon_client(node_addon)
        client.file_delete(path)
        # log the event
        nodelogger = DropboxNodeLogger(node=node, auth=auth, path=path)
        nodelogger.log(NodeLog.FILE_REMOVED, save=True)
        return None
    raise HTTPError(http.BAD_REQUEST)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dropbox', 'node')
def dropbox_upload(node_addon, auth, **kwargs):
    node = node_addon.owner
    # Route may or may not have a path
    path = kwargs.get('path', node_addon.folder)
    client = get_node_addon_client(node_addon)
    file_obj = request.files.get('file', None)
    node = node_addon.owner
    if path and file_obj and client:
        filepath = os.path.join(path, file_obj.filename)
        metadata = client.put_file(filepath, file_obj)  # TODO Cast to Hgrid
        permissions = {
            'edit': node.can_edit(auth),
            'view': node.can_view(auth)
        }
        # Log the event
        nodelogger = DropboxNodeLogger(node=node, auth=auth, path=filepath)
        nodelogger.log(NodeLog.FILE_ADDED, save=True)
        return metadata_to_hgrid(metadata, node=node, permissions=permissions)
    raise HTTPError(http.BAD_REQUEST)

# TODO(sloria): Test me
# TODO(sloria): Put in utils?
def make_file_response(fileobject, metadata):
    """Builds a response from a file-like object and metadata returned by
    a Dropbox client.
    """
    resp = make_response(fileobject.read())
    disposition = 'attachment; filename={0}'.format(metadata['path'])
    resp.headers['Content-Disposition'] = disposition
    resp.headers['Content-Type'] = metadata.get('mime_type', 'application/octet-stream')
    return resp


@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_download(path, node_addon, **kwargs):
    if not path:
        raise HTTPError(http.BAD_REQUEST)
    client = get_node_addon_client(node_addon)
    revision = request.args.get('rev')
    fileobject, metadata = client.get_file_and_metadata(path, rev=revision)
    return make_file_response(fileobject, metadata)

@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_get_revisions(path, node_addon, auth, **kwargs):
    node = node_addon.owner
    client = get_node_addon_client(node_addon)
    # Get metadata for each revision of the file
    revisions = client.revisions(path)
    # Add download links
    for revision in revisions:
        revision['download'] = node.web_url_for('dropbox_download',
            path=path, rev=revision['rev'])
        revision['view'] = node.web_url_for('dropbox_view_file',
            path=path, rev=revision['rev'])
    return {
        'result': revisions,
        'status': 200
    }, 200

# TODO(sloria): Test me
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
    rev = request.args.get('rev')
    rendered = render_dropbox_file(file_obj, client=client, rev=rev)
    cleaned_path = clean_path(path)
    response = {
        'revisionsUrl': node.api_url_for('dropbox_get_revisions', path=cleaned_path),
        'file_name': get_file_name(path),
        'render_url': node.api_url_for('dropbox_render_file', path=cleaned_path),
        'download_url': file_obj.download_url,
        'rendered': rendered,
    }
    response.update(serialize_node(node, auth, primary=True))
    return response

##### MFR Rendering #####

# TODO(sloria): Test me
@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_render_file(path, node_addon, auth, **kwargs):
    node = node_addon.owner
    file_obj = DropboxFile.find_one(Q('node', 'eq', node) & Q('path', 'eq', path))
    client = get_node_addon_client(node_addon)
    rev = request.args.get('rev')
    return render_dropbox_file(file_obj, client=client, rev=rev)
