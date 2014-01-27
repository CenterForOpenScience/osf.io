import os
import re
import urllib
import datetime
import pygments
import httplib as http

from hurry.filesize import size, alternative

from framework import request, make_response
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import models
from website import settings
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from ..api import GitHub, raw_url
from .util import MESSAGES


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_file(*args, **kwargs):

    github = kwargs['node_addon']

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')

    connection = GitHub.from_settings(github.user_settings)

    name, data, _ = connection.file(github.user, github.repo, path, ref=ref)
    if data is None:
        raise HTTPError(http.NOT_FOUND)

    # Build response
    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )

    # Add binary MIME type if extension missing
    _, ext = os.path.splitext(name)
    if not ext:
        resp.headers['Content-Type'] = 'application/octet-stream'

    return resp


# TODO: Remove unnecessary API calls
@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_view_file(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    github = kwargs['node_addon']

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    connection = GitHub.from_settings(github.user_settings)

    repo = connection.repo(github.user, github.repo)

    # Get branch / commit
    branch = request.args.get('branch', repo['default_branch'])
    sha = request.args.get('sha', branch)

    file_name, data, size = connection.file(
        github.user, github.repo, path, ref=sha,
    )

    # Get file URL
    if repo is None or repo['private']:
        url = os.path.join(node.api_url, 'github', 'file', path)
    else:
        url = raw_url(github.user, github.repo, sha, path)

    # Get file history
    start_sha = (sha or branch) if node.is_registration else branch
    commits = connection.history(github.user, github.repo, path, sha=start_sha)
    for commit in commits:
        # TODO: Parameterize or remove hotlinking
        #if repo['private']:
        commit['download'] = os.path.join(node.api_url, 'github', 'file', path) + '?ref=' + commit['sha']
        #else:
        #    commit['download'] = raw_url(github.user, github.repo, commit['sha'], path)
        commit['view'] = os.path.join(node.url, 'github', 'file', path) + '?sha=' + commit['sha'] + '&branch=' + branch

    # Get current commit
    shas = [
        commit['sha']
        for commit in commits
    ]
    current_sha = sha if sha in shas else shas[0]

    # Pasted from views/file.py #
    # TODO: Replace with modular-file-renderer

    _, file_ext = os.path.splitext(path.lower())

    is_img = False
    for fmt in settings.IMG_FMTS:
        fmt_ptn = '^.{0}$'.format(fmt)
        if re.search(fmt_ptn, file_ext):
            is_img = True
            break

    if is_img:

        rendered='<img src="{url}/" />'.format(
            url=url,
        )

    else:

        if size > settings.MAX_RENDER_SIZE:
            rendered = (
                '<p>This file is too large to be rendered online. '
                'Please <a href={url} download={name}>download the file</a> to view it locally.</p>'
            ).format(
                url=url,
                name=file_name,
            )

        else:
            try:
                rendered = pygments.highlight(
                    data,
                    pygments.lexers.guess_lexer_for_filename(path, data),
                    pygments.formatters.HtmlFormatter()
                )
            except pygments.util.ClassNotFound:
                rendered = (
                    '<p>This file cannot be rendered online. '
                    'Please <a href={url} download={name}>download the file</a> to view it locally.</p>'
                ).format(
                    url=url,
                    name=file_name,
                )

    # End pasted code #

    rv = {
        'file_name': file_name,
        'current_sha': current_sha,
        'rendered': rendered,
        'download_url': url,
        'commits': commits,
    }
    rv.update(_view_project(node, user, primary=True))
    return rv


@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github', 'node')
def github_upload_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = kwargs['node_addon']
    now = datetime.datetime.utcnow()

    path = kwargs.get('path', '')

    branch = request.args.get('branch')
    sha = request.args.get('sha')

    if branch is None:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(github.user_settings)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    content = upload.read()

    # Get SHA of existing file if present; requires an additional call to the
    # GitHub API
    tree = connection.tree(github.user, github.repo, sha=sha or branch)
    existing = [
        thing
        for thing in tree['tree']
        if thing['path'] == os.path.join(path, filename)
    ]
    sha = existing[0]['sha'] if existing else None

    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    data = connection.upload_file(
        github.user, github.repo, os.path.join(path, filename),
        MESSAGES['update' if sha else 'add'], content, sha=sha, branch=branch,
        author=author,
    )

    if data is not None:

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
                'github': {
                    'user': github.user,
                    'repo': github.repo,
                    'url': node.api_url + 'github/file/{0}/?ref={1}'.format(
                        os.path.join(path, filename),
                        data['commit']['sha']
                    ),
                },
            },
            user=user,
            api_key=None,
            log_date=now,
        )

        ref = urllib.urlencode({
            'branch': branch,
        })

        parent_uid = 'github:{0}'.format(github._id)
        if path:
            parent_uid += ':' + path

        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.')

        info = {
            'name': filename,
            'uid': os.path.join('__repo__', data['content']['path']),
            'parent_uid': parent_uid,
            'can_edit': True,
            'ext': ext,
            'size': [
                data['content']['size'],
                size(data['content']['size'], system=alternative)
            ],
            'type': 'file',
            'download': node.api_url + 'github/file/{0}/'.format(os.path.join(path, filename)),
            'view': os.path.join(node.url, 'github', 'file', path, filename),
            'delete': node.api_url + 'github/file/{0}/'.format(data['content']['path']),
            'data': {
                'sha': data['content']['sha'],
                'branch': branch,
            }
        }

        info['view'] += '?' + ref
        info['download'] += '?' + ref
        info['delete'] += '?' + ref

        return [info]

    raise HTTPError(http.BAD_REQUEST)

@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github', 'node')
def github_delete_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = kwargs['node_addon']

    now = datetime.datetime.utcnow()

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    sha = request.json.get('sha')
    if sha is None:
        raise HTTPError(http.BAD_REQUEST)

    branch = request.json.get('branch')

    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    connection = GitHub.from_settings(github.user_settings)

    data = connection.delete_file(
        github.user, github.repo, path, MESSAGES['delete'],
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
                'user': github.user,
                'repo': github.repo,
            },
        },
        user=user,
        api_key=None,
        log_date=now,
    )

    return {}


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_starball(*args, **kwargs):

    github = kwargs['node_addon']
    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('ref')

    connection = GitHub.from_settings(github.user_settings)
    headers, data = connection.starball(github.user, github.repo, archive, ref)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


