# -*- coding: utf-8 -*-

import os
import hashlib
import logging
import datetime
import httplib as http

from modularodm import Q
from modularodm.exceptions import ModularOdmException
from flask import request, make_response

from framework.exceptions import HTTPError
from framework.utils import secure_filename
from framework.flask import redirect  # VOL-aware redirect

from website import models
from website.project.decorators import (
    must_be_contributor_or_public, must_have_permission, must_have_addon,
    must_not_be_registration
)
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.project.model import has_anonymous_link
from website.addons.base.views import check_file_guid
from website.util import rubeus, permissions
from website.util.mimetype import get_mimetype

from website.addons.github import settings as github_settings
from website.addons.github.exceptions import (
    NotFoundError, EmptyRepoError, TooBigError
)
from website.addons.github.api import GitHub, ref_to_params, build_github_urls
from website.addons.github.model import GithubGuidFile
from website.addons.github.utils import MESSAGES, get_path


logger = logging.getLogger(__name__)


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_file(**kwargs):

    node_settings = kwargs['node_addon']

    path = get_path(kwargs)

    ref = request.args.get('sha')
    connection = GitHub.from_settings(node_settings.user_settings)

    try:
        name, data, _ = connection.file(
            node_settings.user, node_settings.repo, path, ref=ref
        )
    except TooBigError:
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': 'File too large',
                'message_long': 'This file is too large to download through '
                'the GitHub API.',
            },
        )
    if data is None:
        raise HTTPError(http.NOT_FOUND)

    # Build response
    resp = make_response(data)
    mimetype = get_mimetype(path, data)
    # Add binary MIME type if mimetype not found
    if mimetype is None:
        resp.headers['Content-Type'] = 'application/octet-stream'
    else:
        resp.headers['Content-Type'] = mimetype

    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name)

    return resp


def get_cache_file(path, sha):
    return '{0}_{1}.html'.format(
        hashlib.md5(path.encode('utf-8', 'ignore')).hexdigest(),
        sha,
    )


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_view_file(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    path = get_path(kwargs)
    file_name = os.path.split(path)[1]

    # Get branch / commit
    branch = request.args.get('branch')
    sha = request.args.get('sha', branch)
    ref = sha or branch

    connection = GitHub.from_settings(node_settings.user_settings)

    # Get current file for delete url
    current_file = connection.contents(
        user=node_settings.user, repo=node_settings.repo, path=path,
        ref=sha or branch)

    anonymous = has_anonymous_link(node, auth)
    try:
        # If GUID has already been created, we won't redirect, and can check
        # whether the file exists below
        guid = GithubGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', path)
        )

    except ModularOdmException:
        # If GUID doesn't exist, check whether file exists before creating
        commits = connection.history(
            node_settings.user, node_settings.repo, path, ref,
        )
        if not commits:
            raise HTTPError(http.NOT_FOUND)
        guid = GithubGuidFile(
            node=node,
            path=path,
        )
        guid.save()

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    # Get default branch if neither SHA nor branch is provided
    if ref is None:
        repo = connection.repo(node_settings.user, node_settings.repo)
        ref = branch = repo.default_branch

    # Get file history; use SHA or branch if registered, else branch
    start_sha = ref if node.is_registration else branch
    commits = connection.history(
        node_settings.user, node_settings.repo, path, sha=start_sha
    )

    # Get current commit
    shas = [
        commit['sha']
        for commit in commits
    ]
    if not shas:
        raise HTTPError(http.NOT_FOUND)
    current_sha = sha if sha in shas else shas[0]

    # Get file URL
    download_url = '/' + guid._id + '/download/' + ref_to_params(branch, current_sha)
    render_url = os.path.join(
        node.api_url, 'github', 'file', path, 'render'
    ) + '/' + ref_to_params(branch, current_sha)

    delete_url = None
    if current_file:
        delete_url = node.api_url_for('github_delete_file', path=path) + ref_to_params(branch, current_file.sha)

    for commit in commits:
        commit['download'] = (
            '/' + guid._id + '/download/' + ref_to_params(sha=commit['sha'])
        )
        commit['view'] = (
            '/' + guid._id + '/' + ref_to_params(branch, sha=commit['sha'])
        )
        if anonymous:
            commit['name'] = 'A user'
            commit['email'] = ''

    # Get or create rendered file
    cache_file = get_cache_file(
        path, current_sha,
    )
    rendered = get_cache_content(node_settings, cache_file)
    if rendered is None:
        try:
            _, data, size = connection.file(
                node_settings.user, node_settings.repo, path, ref=sha,
            )
        except TooBigError:
            rendered = 'File too large to download.'
        if rendered is None:
            # Skip if too large to be rendered.
            if github_settings.MAX_RENDER_SIZE is not None and size > github_settings.MAX_RENDER_SIZE:
                rendered = 'File too large to render; download file to view it.'
            else:
                rendered = get_cache_content(
                    node_settings, cache_file, start_render=True,
                    file_path=file_name, file_content=data, download_path=download_url,
                )

    rv = {
        'node': {
            'id': node._id,
            'title': node.title
        },
        'file_name': file_name,
        'files_page_url': node.web_url_for('collect_file_trees'),
        'current_sha': current_sha,
        'render_url': render_url,
        'rendered': rendered,
        'download_url': download_url,
        'delete_url': delete_url,
        'commits': commits,
    }
    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_have_permission(permissions.WRITE)
@must_not_be_registration
@must_have_addon('github', 'node')
def github_upload_file(auth, node_addon, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = auth.user
    now = datetime.datetime.utcnow()

    path = get_path(kwargs, required=False) or ''

    branch = request.args.get('branch')
    sha = request.args.get('sha')

    if branch is None:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(node_addon.user_settings)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    content = upload.read()

    # Check max file size
    upload.seek(0, os.SEEK_END)
    size = upload.tell()

    if size > node_addon.config.max_file_size * 1024 * 1024:
        raise HTTPError(http.BAD_REQUEST)

    # Get SHA of existing file if present; requires an additional call to the
    # GitHub API
    try:
        tree = connection.tree(
            node_addon.user, node_addon.repo, sha=sha or branch
        ).tree
    except EmptyRepoError:
        tree = []
    except NotFoundError:
        raise HTTPError(http.BAD_REQUEST)
    existing = [
        thing
        for thing in tree
        if thing.path == os.path.join(path, filename)
    ]
    sha = existing[0].sha if existing else None

    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    if existing:
        data = connection.update_file(
            node_addon.user, node_addon.repo, os.path.join(path, filename),
            MESSAGES['update'], content, sha=sha, branch=branch, author=author
        )
    else:
        data = connection.create_file(
            node_addon.user, node_addon.repo, os.path.join(path, filename),
            MESSAGES['add'], content, branch=branch, author=author
        )

    if data is not None:

        ref = ref_to_params(sha=data['commit'].sha)
        view_url = os.path.join(
            node.url, 'github', 'file', path, filename
        ) + '/' + ref
        download_url = os.path.join(
            node.url, 'github', 'file', path, filename, 'download'
        ) + '/' + ref

        node.add_log(
            action=(
                'github_' + (
                    models.NodeLog.FILE_UPDATED
                    if sha
                    else models.NodeLog.FILE_ADDED
                )
            ),
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'path': os.path.join(path, filename),
                'urls': {
                    'view': view_url,
                    'download': download_url,
                },
                'github': {
                    'user': node_addon.user,
                    'repo': node_addon.repo,
                    'sha': data['commit'].sha,
                },
            },
            auth=auth,
            log_date=now,
        )

        # Fail if file size is not provided; this happens when the file was
        # too large to upload to GitHub
        if data['content'].size is None:
            logger.error(
                'Could not upload file {0} to GitHub: No size provided'.format(
                    filename
                )
            )
            raise HTTPError(http.BAD_REQUEST)

        info = {
            'addon': 'github',
            'name': filename,
            'size': [
                data['content'].size,
                rubeus.format_filesize(data['content'].size),
            ],
            'kind': 'file',
            'urls': build_github_urls(
                data['content'], node.url, node.api_url, branch, sha,
            ),
            'permissions': {
                'view': True,
                'edit': True,
            },
        }

        return info, 201

    raise HTTPError(http.BAD_REQUEST)

@must_have_permission(permissions.WRITE)
@must_not_be_registration
@must_have_addon('github', 'node')
def github_delete_file(auth, node_addon, **kwargs):

    node = kwargs['node'] or kwargs['project']

    now = datetime.datetime.utcnow()

    # Must remove trailing slash, else GitHub fails silently on delete
    path = get_path(kwargs).rstrip('/')

    sha = request.args.get('sha')
    if sha is None:
        raise HTTPError(http.BAD_REQUEST)

    branch = request.args.get('branch')

    author = {
        'name': auth.user.fullname,
        'email': '{0}@osf.io'.format(auth.user._id),
    }

    connection = GitHub.from_settings(node_addon.user_settings)

    data = connection.delete_file(
        node_addon.user, node_addon.repo, path, MESSAGES['delete'],
        sha=sha, branch=branch, author=author,
    )

    if data is None:
        raise HTTPError(http.BAD_REQUEST)

    node.add_log(
        action='github_' + models.NodeLog.FILE_REMOVED,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'path': path,
            'github': {
                'user': node_addon.user,
                'repo': node_addon.repo,
            },
        },
        auth=auth,
        log_date=now,
    )

    return {}


# TODO Add me Test me
@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_starball(node_addon, **kwargs):

    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('sha', 'master')

    connection = GitHub.from_settings(node_addon.user_settings)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, archive, ref
    )

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp

# File rendering #

@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_get_rendered_file(**kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    path = get_path(kwargs)
    sha = request.args.get('sha')

    cache_file = get_cache_file(path, sha)
    return get_cache_content(node_settings, cache_file)
