import os
import urllib
import datetime
import httplib as http

from hurry.filesize import size, alternative

from framework import request, redirect, make_response, Q
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.addons.base.views import check_file_guid

from ..api import GitHub, ref_to_params, _build_github_urls
from ..model import GithubGuidFile
from .. import settings as github_settings
from .util import MESSAGES


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_file(**kwargs):

    github = kwargs['node_addon']

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('sha')
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

    # Get branch / commit
    branch = request.args.get('branch')
    sha = request.args.get('sha', branch)
    ref = sha or branch

    connection = GitHub.from_settings(node_settings.user_settings)

    try:
        # If GUID has already been created, we won't redirect, and can check
        # whether the file exists below
        guid = GithubGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', path)
        )
    except:
        # If GUID doesn't exist, check whether file exists before creating
        commits = connection.history(
            node_settings.user, node_settings.repo, path, ref,
        )
        if commits is None:
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
    render_url = '/api/v1/' + guid._id + '/render/' + ref_to_params(branch, current_sha)

    for commit in commits:
        commit['download'] = (
            '/' + guid._id + '/download/' + ref_to_params(sha=commit['sha'])
        )
        commit['view'] = (
            '/' + guid._id + '/' + ref_to_params(branch, sha=commit['sha'])
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
                file_path=file_name, file_content=data, download_path=download_url,
            )

    rv = {
        'file_name': file_name,
        'current_sha': current_sha,
        'render_url': render_url,
        'rendered': rendered,
        'download_url': download_url,
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
        for thing in tree.tree
        if thing.path == os.path.join(path, filename)
    ]
    sha = existing[0].sha if existing else None

    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    if existing:
        data = connection.update_file(
            github.user, github.repo, os.path.join(path, filename),
            MESSAGES['update'], content, sha=sha, branch=branch, author=author
        )
    else:
        data = connection.create_file(
            github.user, github.repo, os.path.join(path, filename),
            MESSAGES['update'], content, branch=branch, author=author
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
                    'user': github.user,
                    'repo': github.repo,
                    'sha': data['commit'].sha,
                },
            },
            auth=auth,
            log_date=now,
        )

        info = {
            'addon': 'github',
            'name': filename,
            'size': [
                data['content'].size,
                size(data['content'].size, system=alternative)
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


# TODO Add me Test me
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
