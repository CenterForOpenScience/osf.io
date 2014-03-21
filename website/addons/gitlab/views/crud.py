import os
import base64
import urllib
import httplib as http
from dateutil.parser import parse as parse_date

from framework import Q
from framework.auth import get_user
from framework.flask import request, redirect, make_response
from framework.exceptions import HTTPError

from website.project.decorators import (
    must_be_contributor_or_public, must_not_be_registration,
    must_have_permission, must_have_addon,
)
from website.util import rubeus
from website.util.permissions import WRITE
from website.models import NodeLog
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.addons.base.views import check_file_guid
from website.dates import FILE_MODIFIED

from website.addons.gitlab.api import client
from website.addons.gitlab.model import GitlabGuidFile
from website.addons.gitlab.utils import (
    create_node, gitlab_slugify,
    kwargs_to_path, item_to_hgrid, gitlab_to_hgrid, build_urls, refs_to_params
)
from website.addons.gitlab import settings as gitlab_settings


def get_cache_file(path, sha):
    return '{0}_{1}.html'.format(
        urllib.quote_plus(path), sha,
    )


# TODO: Test me @jmcarp
def ref_or_default(node_settings, data):
    """Get the git reference (SHA or branch) from view arguments; return the
    default reference if none is supplied.

    :param AddonGitlabNodeSettings node_settings: Gitlab node settings
    :param dict data: View arguments
    :returns: SHA or branch if reference found, else None

    """
    ref = data.get('sha') or data.get('branch')
    if ref:
        return ref
    if node_settings.project_id:
        project = client.getproject(node_settings.project_id)
        return project['default_branch']
    return None


def create_or_update(node_settings, user_settings, method_name, action,
                     filename, branch, content, auth):
    """
    
    """
    node = node_settings.owner

    if method_name not in ['createfile', 'updatefile']:
        raise ValueError(
            'Argument `method_name` must be one of '
            '("createfile", "updatefile")'
        )
    method = getattr(client, method_name)

    response = method(
        node_settings.project_id, filename, branch, content,
        gitlab_settings.MESSAGES['add'], encoding='base64',
        user_id=user_settings.user_id
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


@must_have_permission(WRITE)
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_upload_file(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    # Lazily configure Gitlab project if not already created
    create_node(node_settings)
    user_settings = auth.user.get_addon('gitlab')

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
    slug = gitlab_slugify(filename)

    response = create_or_update(
        node_settings, user_settings, 'createfile', NodeLog.FILE_ADDED,
        slug, branch, content, auth
    )
    if not response:
        response = create_or_update(
            node_settings, user_settings, 'updatefile', NodeLog.FILE_UPDATED,
            slug, branch, content, auth
        )

    # File created or modified
    if response:
        head, tail = os.path.split(response['file_path'])
        grid_data = item_to_hgrid(
            node,
            {
                'type': 'blob',
                'name': tail,
            },
            path=head,
            permissions={
                'view': True,
                'edit': True,
            },
            branch=branch
        )
        return grid_data, 201

    # File not modified
    # TODO: Test whether something broke
    return {'actionTaken': None}


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

    # Don't crash if Gitlab project hasn't been created yet
    if not node_settings.project_id:
        return []

    path = kwargs.get('path', '')
    branch = kwargs.get('branch')
    sha = kwargs.get('sha')

    tree = client.listrepositorytree(
        node_settings.project_id, path=path, ref_name=sha or branch
    )
    permissions = {
        'view': True,
        'edit': (
            node.has_permission(auth.user, WRITE)
            and not node.is_registration
        )
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
        contents = client.getfile(node_settings.project_id, path, ref)
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

    branch = request.args.get('branch')
    sha = request.args.get('sha')

    ref = ref_or_default(node_settings, request.args)

    guid, contents = path_to_guid(node_settings, node, path, ref)

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    commits = client.listrepositorycommits(
        node_settings.project_id, ref_name=branch, path=path
    )
    sha = sha or commits[0]['id']
    commit_data = []
    for commit in commits:

        committer_user = get_user(username=commit['author_email'])
        if committer_user:
            committer_name = committer_user.fullname
            committer_url = committer_user.url
        else:
            committer_name = commit['author_name']
            committer_url = 'mailto:{0}'.format(commit['author_email'])
        urls = {
            'sha': commit['id'],
            'view': '/' + guid._id + '/' + refs_to_params(branch, sha=commit['id']),
            'download': '/' + guid._id + '/download/' + refs_to_params(sha=commit['id']),
            'date': parse_date(commit['created_at']).strftime(FILE_MODIFIED),
            'committer_name': committer_name,
            'committer_url': committer_url,
        }
        commit_data.append(urls)

    contents = contents or client.getfile(
        node_settings.project_id, path, ref
    )

    contents = base64.b64decode(contents['content'])

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
    ref = ref_or_default(node_settings, request.args)

    contents = client.getfile(node_settings.project_id, path, ref)

    if contents is False:
        raise HTTPError(http.NOT_FOUND)

    contents = base64.b64decode(contents['content'])

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


@must_have_permission(WRITE)
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_delete_file(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
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
            params={
                'project': node.parent_id,
                'node': node._id,
                'path': path,
                'gitlab': {
                    'branch': branch,
                }
            },
            auth=auth,
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
