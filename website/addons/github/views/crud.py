# -*- coding: utf-8 -*-

import os
import logging
import datetime
import httplib as http

from flask import request, make_response

from framework.exceptions import HTTPError
from framework.utils import secure_filename

from website import models
from website.project.decorators import (
    must_be_contributor_or_public, must_have_permission, must_have_addon,
    must_not_be_registration
)
from website.util import rubeus, permissions
from website.util.mimetype import get_mimetype

from website.addons.github.exceptions import (
    NotFoundError, EmptyRepoError, TooBigError
)
from website.addons.github.api import GitHub, ref_to_params, build_github_urls
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
