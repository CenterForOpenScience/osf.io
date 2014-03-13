import os
import base64
import urllib
import httplib as http

from framework import Q
from framework.flask import request, redirect, make_response
from framework.exceptions import HTTPError

from website.project.decorators import (
    must_be_contributor_or_public, must_not_be_registration,
    must_have_permission, must_have_addon,
)
from website.util import rubeus
from website.models import NodeLog
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.addons.base.views import check_file_guid

from website.addons.gitlab.api import client
from website.addons.gitlab.model import GitlabGuidFile
from website.addons.gitlab.utils import (
    kwargs_to_path, gitlab_to_hgrid, build_urls, refs_to_params
)
from website.addons.gitlab import settings as gitlab_settings


def get_cache_file(path, sha):
    return '{0}_{1}.html'.format(
        urllib.quote_plus(path), sha,
    )


def ref_or_default(node_settings, kwargs):
    ref = kwargs.get('sha') or kwargs.get('branch')
    if not ref:
        project = client.getproject(node_settings.project_id)
        ref = project['default_branch']
    return ref


def create_or_update(node_settings, method, action, filename, branch, content,
                     auth):
    """
    
    """
    node = node_settings.owner

    attr = getattr(client, method)
    response = attr(
        node_settings.project_id, filename, branch, content,
        gitlab_settings.MESSAGES['add']
    )

    if response:
        urls = build_urls(
            node, {'type': 'blob'}, response['file_path'],
            branch=branch
        )
        node_settings.owner.add_log(
            action='gitlab_' + action,
            params={
                'project': node.parent_id,
                'node': node._id,
                'path': response['file_path'],
                'urls': urls,
                'gitlab': {
                    'branch': branch,
                }
            },
            auth=auth,
        )

    return response


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_upload_file(**kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']

    path = kwargs_to_path(kwargs, required=False)
    branch = ref_or_default(node_settings, kwargs)

    upload = request.files.get('file')
    content = upload.read()
    content = base64.b64encode(content)

    # Check max file size
    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    if size > node_settings.config.max_file_size * 1024 * 1024:
        raise HTTPError(http.BAD_REQUEST)

    filename = os.path.join(path, upload.filename)
    response = create_or_update(
        node_settings, 'createfile', NodeLog.FILE_ADDED,
        filename, branch, content, auth
    )
    if not response:
        response = create_or_update(
            node_settings, 'updatefile', NodeLog.FILE_UPDATED,
            filename, branch, content, auth
        )

    if not response:
        # TODO: This should raise an HTTPError
        return {'message': 'Could not upload file'}, http.BAD_REQUEST


def gitlib_hgrid_root(node_settings, auth, **kwargs):

    node = node_settings.owner
    branch = kwargs.get('branch')
    sha = kwargs.get('sha')

    permissions = {
        'edit': node.can_edit(auth=auth),
        'view': True,
    }
    urls = build_urls(
        node, {'type': 'tree'}, path='',
        branch=branch, sha=sha
    )
    return [rubeus.build_addon_root(
        node_settings,
        name=None,
        urls=urls,
        permissions=permissions,
    )]


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_list_files(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    path = kwargs.get('path', '')
    branch = kwargs.get('branch')
    sha = kwargs.get('sha')

    tree = client.listrepositorytree(
        node_settings.project_id, path=path, ref_name=sha or branch
    )
    permissions = {
        'view': True,
        'edit': node.has_permission(auth.user, 'write')
    }

    return gitlab_to_hgrid(node, tree, path, permissions, branch, sha)


def path_to_guid(node_settings, node, path, ref):
    """

    :returns: Tuple of GUID and contents; contents will be empty if we don't
        need to check existence

    """
    contents = None

    try:
        # If GUID has already been created, we won't redirect, and can check
        # whether the file exists below
        guid = GitlabGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', path)
        )
    except:
        # If GUID doesn't exist, check whether file exists before creating
        contents = client.getrawblob(node_settings.project_id, ref, path)
        if contents is False:
            raise HTTPError(http.NOT_FOUND)
        guid = GitlabGuidFile(
            node=node,
            path=path,
        )
        guid.save()

    return guid, contents


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_view_file(**kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node = node_settings.owner

    path = kwargs_to_path(kwargs, required=True)
    _, filename = os.path.split(path)

    branch = kwargs.get('branch')
    sha = kwargs.get('sha')

    ref = ref_or_default(node_settings, kwargs)

    guid, contents = path_to_guid(node_settings, node, path, ref)

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    if node.is_registration:
        if sha is None:
            raise ValueError('Must specify SHA for registration files')
        commit_data = []
    else:
        commits = [
            commit['id'] for commit in
            client.listrepositorycommits(node_settings.project_id)
        ]
        sha = sha or commits[0]
        commit_data = []
        for commit in commits:
            urls = {
                'sha': commit,
                'view': '/' + guid._id + '/' + refs_to_params(branch, sha=commit),
                'download': '/' + guid._id + '/download/' + refs_to_params(sha=commit),
            }
            commit_data.append(urls)

    contents = contents or client.getrawblob(
        node_settings.project_id, ref, path
    )

    contents = base64.b64decode(contents)

    # Get file URL
    download_url = '/' + guid._id + '/download/' + refs_to_params(branch, sha)
    render_url = os.path.join(
        node.api_url, 'gitlab', 'files', path, 'render'
    ) + '/' + refs_to_params(branch, sha)


    # Get or create rendered file
    cache_file = get_cache_file(path, sha)
    rendered = get_cache_content(node_settings, cache_file)
    if rendered is None:
        # TODO: Skip large files
        rendered = get_cache_content(
            node_settings, cache_file, start_render=True,
            file_path=filename, file_content=contents,
            download_path=download_url,
        )

    out = {
        'file_name': filename,
        'sha': sha,
        'render_url': render_url,
        'download_url': download_url,
        'rendered': rendered,
        'commits': commit_data,
    }
    out.update(_view_project(node, auth, primary=True))
    return out


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_download_file(**kwargs):

    node_settings = kwargs['node_addon']

    path = kwargs_to_path(kwargs, required=True)
    ref = ref_or_default(node_settings, kwargs)

    contents = client.getrawblob(node_settings.project_id, ref, path)

    if contents is False:
        raise HTTPError(http.NOT_FOUND)

    contents = base64.b64decode(contents)

    # Build response
    resp = make_response(contents)
    _, filename = os.path.split(path)
    disposition = 'attachment; filename={0}'.format(filename)
    resp.headers['Content-Disposition'] = disposition

    # Add binary MIME type if extension missing
    _, ext = os.path.splitext(filename)
    if not ext:
        resp.headers['Content-Type'] = 'application/octet-stream'

    return resp


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_delete_file(**kwargs):

    node_settings = kwargs['node_addon']

    path = kwargs_to_path(kwargs, required=True)
    branch = ref_or_default(node_settings, kwargs)


    success = client.deletefile(
        node_settings.project_id, path, branch,
        gitlab_settings.MESSAGES['delete']
    )

    if success:
        node_settings.owner.add_log(
            action='gitlab_' + NodeLog.FILE_REMOVED,
        )
    else:
        # TODO: This should raise an HTTPError
        return {'message': 'Could not delete file'}, http.BAD_REQUEST


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_get_rendered_file(**kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    path = kwargs_to_path(kwargs, required=True)

    try:
        sha = request.args['sha']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

    cache_file = get_cache_file(path, sha)
    return get_cache_content(node_settings, cache_file)
