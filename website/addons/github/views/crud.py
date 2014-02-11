import os
import urllib
import datetime
import httplib as http

from hurry.filesize import size, alternative

from framework import request, make_response
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content

from ..api import GitHub, ref_to_params, _build_github_urls
from .. import settings as github_settings
from .util import MESSAGES


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_file(**kwargs):

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


def get_cache_file(path, sha):
    return '{0}_{1}.html'.format(
        urllib.quote_plus(path), sha,
    )

# TODO: Remove unnecessary API calls
@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_view_file(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)
    file_name = os.path.split(path)[1]

    connection = GitHub.from_settings(node_settings.user_settings)

    repo = connection.repo(node_settings.user, node_settings.repo)

    # Get branch / commit
    branch = request.args.get('branch', repo['default_branch'])
    sha = request.args.get('sha', branch)

    # Get file URL
    url = os.path.join(node.api_url, 'github', 'file', path)

    # Get file history
    start_sha = (sha or branch) if node.is_registration else branch
    commits = connection.history(
        node_settings.user, node_settings.repo, path, sha=start_sha
    )

    # Get current commit
    shas = [
        commit['sha']
        for commit in commits
    ]
    current_sha = sha if sha in shas else shas[0]

    for commit in commits:
        commit['download'] = (
            os.path.join(node.api_url, 'github', 'file', path) +
            '?ref=' + ref_to_params(sha=commit['sha'])
        )
        commit['view'] = (
            os.path.join(node.url, 'github', 'file', path)
            + '?' + ref_to_params(branch, commit['sha'])
        )

    # Get or create rendered file
    cache_file = get_cache_file(
        path, current_sha,
    )
    rendered = get_cache_content(node_settings, cache_file)
    if rendered is None:
        _, data, size = connection.file(
            node_settings.user, node_settings.repo, path, ref=sha,
        )
        # Skip if too large to be rendered.
        if github_settings.MAX_RENDER_SIZE is not None and size > github_settings.MAX_RENDER_SIZE:
            rendered = 'File too large to render; download file to view it'
        else:
            rendered = get_cache_content(
                node_settings, cache_file, start_render=True,
                file_path=file_name, file_content=data, download_path=url,
            )

    rv = {
        'file_name': file_name,
        'current_sha': current_sha,
        'render_url': url + '/render/' + '?sha=' + current_sha,
        'rendered': rendered,
        'download_url': url,
        'commits': commits,
    }
    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github', 'node')
def github_upload_file(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    user = auth.user
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
            auth=auth,
            log_date=now,
        )

        info = {
            'addon': 'github',
            'name': filename,
            'size': [
                data['content']['size'],
                size(data['content']['size'], system=alternative)
            ],
            'kind': 'file',
            'urls': _build_github_urls(
                data['content'], node.url, node.api_url, branch, sha,
            ),
            'permissions': {
                'view': True,
                'edit': True,
            },
        }

        return info, 201

    raise HTTPError(http.BAD_REQUEST)

@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github', 'node')
def github_delete_file(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    github = kwargs['node_addon']

    now = datetime.datetime.utcnow()

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    sha = request.args.get('sha')
    if sha is None:
        raise HTTPError(http.BAD_REQUEST)

    branch = request.args.get('branch')

    author = {
        'name': auth.user.fullname,
        'email': '{0}@osf.io'.format(auth.user._id),
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
        auth=auth,
        log_date=now,
    )

    return {}


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_starball(**kwargs):

    github = kwargs['node_addon']
    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('ref')

    connection = GitHub.from_settings(github.user_settings)
    headers, data = connection.starball(github.user, github.repo, archive, ref)

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
    path = kwargs.get('path')
    sha = request.args.get('sha')

    cache_file = get_cache_file(path, sha)
    return get_cache_content(node_settings, cache_file)
