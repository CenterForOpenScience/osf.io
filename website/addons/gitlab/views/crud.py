import os
import base64
import urllib
import logging
import httplib as http
from mako.template import Template
from flask import request, redirect, make_response

from framework.exceptions import HTTPError
from framework.analytics import update_counters

from website import settings
from website.project.decorators import (
    must_be_contributor_or_public, must_not_be_registration,
    must_have_permission, must_have_addon,
)
from website.util import rubeus
from website.util.permissions import WRITE
from website.models import NodeLog
from website.project.views.file import get_cache_content
from website.addons.base import AddonError
from website.addons.base.views import check_file_guid
from website.project import utils

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab.model import GitlabGuidFile
from website.addons.gitlab.utils import (
    setup_user, setup_node, gitlab_slugify,
    kwargs_to_path, build_full_urls, build_guid_urls,
    item_to_hgrid, gitlab_to_hgrid,
    serialize_commit, ref_or_default, get_branch_and_sha,
    get_default_file_sha,
    GitlabNodeLogger
)
from website.addons.gitlab import settings as gitlab_settings


logger = logging.getLogger(__name__)


def get_cache_file(path, sha):
    return '{0}_{1}.html'.format(
        urllib.quote_plus(path), sha,
    )


def get_guid(node_settings, path, ref):
    """

    """
    try:
        return GitlabGuidFile.get_or_create(
            node_settings, path, ref, client=client
        )
    except AddonError:
        raise HTTPError(http.NOT_FOUND)


def gitlab_upload_log(node, action, auth, data, branch):

    node_logger = GitlabNodeLogger(
        node, auth=auth, path=data['file_path'],
        branch=branch,
    )
    node_logger.log(action)


# TODO: Test me @jmcarp
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

    try:
        response = method(
            node_settings.project_id, filename, branch, content,
            gitlab_settings.MESSAGES['add'], encoding='base64',
            user_id=user_settings.user_id
        )
    except GitlabError:
        return False

    gitlab_upload_log(node, action, auth, response, branch)
    return response


@must_have_permission(WRITE)
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_upload_file(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    # Lazily configure Gitlab
    setup_user(auth.user)
    setup_node(node, check_ready=True)

    user_settings = auth.user.get_addon('gitlab')

    path = kwargs_to_path(kwargs, required=False)
    branch = ref_or_default(node_settings, request.args)

    upload = request.files.get('file')
    content = upload.read()

    if not content:
        return {'message': 'Cannot upload empty file'}, http.BAD_REQUEST

    content = base64.b64encode(content)

    # Check max file size
    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    if size > node_settings.config.max_file_size * 1024 * 1024:
        raise HTTPError(http.BAD_REQUEST)

    filename = os.path.join(path, upload.filename)
    slug = gitlab_slugify(filename)

    # Attempt to create file; if fails, update
    # TODO: Add an update or create endpoint to GitLab
    response = create_or_update(
        node_settings, user_settings, 'createfile', NodeLog.FILE_ADDED,
        slug, branch, content, auth
    )
    response = response or create_or_update(
        node_settings, user_settings, 'updatefile', NodeLog.FILE_UPDATED,
        slug, branch, content, auth
    )

    # No action taken if create and upload both fail
    # TODO: Make error handling more specific
    if not response:
        return {
            'actionTaken': None,
            'name': filename,
        }

    # File created or modified
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
    return grid_data, http.CREATED


def gitlab_hgrid_root(node_settings, auth, **kwargs):
    """

    """
    node = node_settings.owner

    #
    branch, sha = gitlab_settings.DEFAULT_BRANCH, None
    branches = []

    #
    if node_settings.project_id is not None:
        # TODO: Improve error handling
        gitlab_branches = client.listbranches(node_settings.project_id)
        if not gitlab_branches:
            return None
        branches = [
            each['name']
            for each in branches
        ]
        if branches:
            branch, sha = get_branch_and_sha(node_settings, kwargs)

    permissions = {
        'edit': node.can_edit(auth=auth) and not node.is_registration,
        'view': True,
    }
    urls = build_full_urls(
        node, {'type': 'tree'}, path='',
        branch=branch, sha=sha
    )

    extra = render_branch_picker(branch, sha, branches)

    return [rubeus.build_addon_root(
        node_settings,
        name=None,
        urls=urls,
        permissions=permissions,
        extra=extra,
    )]


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_hgrid_root_public(**kwargs):
    """View function returning the root container for a GitLab repo. This
    view is exposed to allow switching between branches in the file grid
    interface.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return gitlab_hgrid_root(node_settings, auth=auth, **data)


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_list_files(node_addon, auth, path='', **kwargs):

    node = kwargs['node'] or kwargs['project']

    # Don't crash if Gitlab project hasn't been created yet
    if not node_addon.project_id:
        return []

    branch = request.args.get('branch')
    sha = request.args.get('sha')

    tree = client.listrepositorytree(
        node_addon.project_id, path=path, ref_name=sha or branch
    )
    permissions = {
        'view': True,
        'edit': (
            node.has_permission(auth.user, WRITE)
            and not node.is_registration
        )
    }

    return gitlab_to_hgrid(node, tree, path, permissions, branch, sha)


template_path = os.path.join(
    settings.BASE_PATH, 'addons', 'gitlab', 'templates', 'branch_picker.mako'
)
branch_picker_template = Template(open(template_path).read())

def render_branch_picker(branch, sha, branches):
    return branch_picker_template.render(**locals())


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_file_commits(node_addon, **kwargs):
    """

    """
    branch = request.args.get('branch')
    sha = request.args.get('sha')
    ref = ref_or_default(node_addon, request.args)

    path = kwargs_to_path(kwargs, required=True)
    guid = get_guid(node_addon, path, ref)

    commits = client.listrepositorycommits(
        node_addon.project_id, ref_name=branch, path=path
    )
    sha = sha or commits[0]['id']

    commit_data = [
        serialize_commit(node_addon.owner, path, commit, guid, branch)
        for commit in commits
    ]

    return {
        'sha': sha,
        'commits': commit_data,
    }


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_view_file(**kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node = node_settings.owner

    path = kwargs_to_path(kwargs, required=True)
    _, filename = os.path.split(path)

    branch = request.args.get('branch')

    # SHA cannot be None here, since it will be used in `get_cache_file`
    # below
    sha = (
        request.args.get('sha')
        or get_default_file_sha(node_settings, path=path)
    )

    guid = get_guid(node_settings, path, sha)

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    contents = client.getfile(node_settings.project_id, path, sha)
    contents_decoded = base64.b64decode(contents['content'])

    # Get file URL
    commits_url = node.api_url_for(
        'gitlab_file_commits',
        path=path, branch=branch, sha=sha
    )

    guid_urls = build_guid_urls(guid, branch=branch, sha=sha)
    full_urls = build_full_urls(
        node, {'type': 'blob'}, path, branch=branch, sha=sha
    )

    # Get or create rendered file
    cache_file = get_cache_file(path, sha)
    rendered = get_cache_content(node_settings, cache_file)
    if rendered is None:
        # TODO: Skip large files
        rendered = get_cache_content(
            node_settings, cache_file, start_render=True,
            file_path=filename, file_content=contents_decoded,
            download_path=guid_urls['download'],
        )

    out = {
        'file_name': filename,
        'commits_url': commits_url,
        'render_url': full_urls['render'],
        'download_url': guid_urls['download'],
        'rendered': rendered,
    }
    out.update(utils.serialize_node(node, auth, primary=True))
    return out


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
@update_counters('download:{pid}:{path}:{sha}')
@update_counters('download:{nid}:{path}:{sha}')
@update_counters('download:{pid}:{path}')
@update_counters('download:{nid}:{path}')
def gitlab_download_file(**kwargs):

    node_settings = kwargs['node_addon']

    path = kwargs_to_path(kwargs, required=True)
    ref = ref_or_default(node_settings, request.args)

    try:
        contents = client.getfile(node_settings.project_id, path, ref)
    except GitlabError:
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
    branch = ref_or_default(node_settings, request.args)

    try:
        client.deletefile(
            node_settings.project_id, path, branch,
            gitlab_settings.MESSAGES['delete']
        )

        node_logger = GitlabNodeLogger(
            node, auth=auth, path=path,
            branch=branch,
        )
        node_logger.log(NodeLog.FILE_REMOVED)

    except GitlabError:
        raise HTTPError(http.BAD_REQUEST)


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_get_rendered_file(**kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    path = kwargs_to_path(kwargs, required=True)

    sha = (
        request.args.get('sha')
        or get_default_file_sha(node_settings, path)
    )

    cache_file = get_cache_file(path, sha)
    return get_cache_content(node_settings, cache_file)


@must_be_contributor_or_public
@must_have_addon('gitlab', 'node')
def gitlab_osffiles_url(project, node=None, fid=None, vid=None, **kwargs):
    """Redirect pre-GitLab URLs to current URLs. Raises 404 if version is
    specified but not found in routing table.

    """
    node = node or project

    if vid is None:
        return redirect(node.web_url_for('gitlab_download_file', path=fid))

    node_routes = gitlab_settings.COMPAT_ROUTES.get(node._id, {})
    file_versions = node_routes.get(fid, {})
    try:
        return redirect(
            node.web_url_for(
                'gitlab_download_file',
                path=fid,
                branch='master',
                sha=file_versions[vid],
            )
        )
    except KeyError:
        logger.warn('No route found for file {0}:{1}'.format(fid, vid))
        raise HTTPError(http.NOT_FOUND)
