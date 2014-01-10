"""

"""

import os
import json
import datetime
import httplib as http

from hurry.filesize import size, alternative

from framework import request, redirect, make_response
from framework.auth import get_current_user
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import GitHub, tree_to_hgrid
from .auth import oauth_start_url, oauth_get_token

MESSAGES = {
    'add': 'Added via the Open Science Framework',
    'update': 'Updated via the Open Science Framework',
    'delete': 'Deleted via the Open Science Framework',
}


@must_be_contributor
@must_have_addon('github')
def github_set_config(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    github.user = request.json.get('github_user', '')
    github.repo = request.json.get('github_repo', '')
    github.save()


def _page_content(node, github, hotlink=True):

    if github.user is None or github.repo is None:
        return {}

    connect = GitHub.from_settings(github.user_settings)

    branch = request.args.get('branch', None)

    registration_data = (
        github.registration_data.get('branches', [])
        if github.registered
        else []
    )

    # Get data from GitHub API
    branches = connect.branches(github.user, github.repo)
    if branches is None:
        return {}
    if hotlink:
        repo = connect.repo(github.user, github.repo)
        if repo is None or repo['private']:
            hotlink = False

    commit_id, tree = connect.tree(
        github.user, github.repo, branch=branch,
        registration_data=registration_data
    )
    if tree is None:
        return {}

    hgrid = tree_to_hgrid(
        tree['tree'], github.user, github.repo, node,
        ref=commit_id, hotlink=hotlink,
    )
    return {
        'gh_user': github.user,
        'repo': github.repo,
        'has_auth': github.user_settings is not None,
        'api_url': node.api_url,
        'branches': branches,
        'commit_id': commit_id,
        'show_commit_id': branch is not None,
        'grid_data': json.dumps(hgrid),
        'registration_data': json.dumps(registration_data),
    }


@must_be_contributor_or_public
@must_have_addon('github')
def github_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')
    if github:
        rv = {
            'complete': bool(github.short_url),
            'short_url': github.short_url,
        }
        rv.update(github.config.to_json())
        return rv
    raise HTTPError(http.NOT_FOUND)


@must_be_contributor_or_public
@must_have_addon('github')
def github_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    data = _view_project(node, user)

    rv = _page_content(node, github)
    rv.update({
        'addon_page_js': github.config.include_js.get('page'),
        'addon_page_css': github.config.include_css.get('page'),
    })
    rv.update(github.config.to_json())
    rv.update(data)

    return rv


@must_be_contributor_or_public
@must_have_addon('github')
def github_get_repo(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    connect = GitHub.from_settings(github.user_settings)

    data = connect.repo(github.user, github.repo)

    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('github')
def github_download_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')

    connect = GitHub.from_settings(github.user_settings)

    name, data = connect.file(github.user, github.repo, path, ref=ref)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
    return resp


@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github')
def github_upload_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = node.get_addon('github')
    now = datetime.datetime.utcnow()

    path = kwargs.get('path', '')

    ref = request.args.get('ref')

    connect = GitHub.from_settings(github.user_settings)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    content = upload.read()

    # Get SHA of existing file if present; requires an additional call to the
    # GitHub API
    commit_id, tree = connect.tree(github.user, github.repo, branch=ref)
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

    data = connect.upload_file(
        github.user, github.repo, os.path.join(path, filename),
        MESSAGES['update' if sha else 'add'], content, sha=sha, branch=ref,
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
                    'url': node.api_url + 'github/file/{0}/'.format(os.path.join(path, filename)),
                },
            },
            user=user,
            api_key=None,
            log_date=now,
        )

        info = {
            'name': filename,
            'uid': os.path.join('__repo__', data['content']['path']),
            'parent_uid': 'tree:' + '||'.join(['__repo__', path]).strip('||'),
            'size': [
                data['content']['size'],
                size(data['content']['size'], system=alternative)
            ],
            'type': 'file',
            'sha': data['commit']['sha'],
            'url': data['content']['url'],
            'download': node.api_url + 'github/file/{0}/'.format(os.path.join(path, filename)),
        }

        info['download'] += '?ref=' + commit_id
        info['ref'] = commit_id

        return [info]

    raise HTTPError(http.BAD_REQUEST)

@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('github')
def github_delete_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = node.get_addon('github')
    now = datetime.datetime.utcnow()

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')
    sha = request.json.get('sha')
    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    connect = GitHub.from_settings(github.user_settings)

    data = connect.delete_file(
        github.user, github.repo, path, MESSAGES['delete'], sha=sha,
        branch=ref, author=author,
    )

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

    if data is not None:
        return {}

    raise HTTPError(http.BAD_REQUEST)


@must_be_contributor_or_public
@must_have_addon('github')
def github_download_starball(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')
    archive = kwargs.get('archive', 'tar')

    connect = GitHub.from_settings(github.user_settings)

    headers, data = connect.starball(github.user, github.repo, archive)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value
    raise Exception
    return resp


@must_be_contributor
@must_have_addon('github')
def github_set_privacy(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = GitHub.from_settings(github.user_settings)

    connect.set_privacy(github.user, github.repo, private)


@must_be_contributor
@must_have_addon('github')
def github_add_user_auth(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    github_node = node.get_addon('github')
    github_user = user.get_addon('github')

    if github_node is None or github_user is None:
        raise HTTPError(http.BAD_REQUEST)

    github_node.user_settings = github_user
    github_node.save()

    return {}


@must_be_contributor
@must_have_addon('github')
def github_oauth_start(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    user.add_addon('github', 'user')
    github_user = user.get_addon('github')
    github_node = node.get_addon('github')

    github_node.user_settings = github_user
    github_node.save()

    authorization_url, state = oauth_start_url(user, node)

    github_user.oauth_state = state
    github_user.save()

    return redirect(authorization_url)


# TODO: Expose this
def github_oauth_delete_user(*args, **kwargs):

    user = get_current_user()
    github_user = user.get_addon('github')

    github_user.oauth_access_token = None
    github_user.oauth_token_type = None
    github_user.save()

    return {}


@must_be_contributor
@must_have_addon('github')
def github_oauth_delete_node(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github_node = node.get_addon('github')

    github_node.user_settings = None
    github_node.save()

    return {}


def github_oauth_callback(*args, **kwargs):

    verification_key = request.args.get('state')
    user = models.User.load(kwargs.get('uid'))
    node = models.Node.load(kwargs.get('nid'))

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    github_user = user.get_addon('github')
    github_node = node.get_addon('github')

    if github_user.oauth_state != verification_key:
        raise HTTPError(http.BAD_REQUEST)

    code = request.args.get('code')

    if code is not None:

        token = oauth_get_token(code)

        github_user.oauth_state = None
        github_user.oauth_access_token = token['access_token']
        github_user.oauth_token_type = token['token_type']
        github_user.save()

        if github_node:
            github_node.user_settings = github_user
            github_node.save()

    # TODO: Handle redirect with no node
    return redirect(os.path.join(node.url, 'settings'))
