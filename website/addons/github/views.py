"""

"""

import os
import json
import datetime
import httplib as http

from hurry.filesize import size, alternative
from dateutil.parser import parse as dateparse

from framework import request, redirect, make_response
from framework.auth import get_current_user
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import models
from website import settings
from website.project import decorators
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import GitHub, tree_to_hgrid
from .auth import oauth_start_url, oauth_get_token

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}

# All GitHub hooks come from 192.30.252.0/22
HOOKS_IP = '192.30.252.'

def _add_hook_log(node, github, action, path, date, committer, url=None, save=False):

    github_data = {
        'user': github.user,
        'repo': github.repo,
    }
    if url:
        github_data['url'] = '{0}github/file/{1}/'.format(
            node.api_url,
            path
        )

    node.add_log(
        action=action,
        params={
            'project': node.parent_id,
            'node': node._id,
            'path': path,
            'github': github_data,
        },
        user=None,
        foreign_user=committer,
        api_key=None,
        log_date=date,
        save=save,
    )


@decorators.must_be_valid_project
@decorators.must_not_be_registration
@decorators.must_have_addon('github', 'node')
def github_hook_callback(*args, **kwargs):
    """Add logs for commits from outside OSF.

    """
    # Request must come from GitHub hooks IP
    if HOOKS_IP not in request.remote_addr:
        raise HTTPError(http.BAD_REQUEST)

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] in MESSAGES.values():
            continue

        date = dateparse(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_ADDED,
                path, date, committer, url=True,
            )
        for path in commit.get('updated', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_UPDATED,
                path, date, committer, url=True,
            )
        for path in commit.get('removed', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()


@must_be_contributor
@must_have_addon('github', 'node')
def github_set_config(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    github_user = user.get_addon('github')
    github_node = node.get_addon('github')

    # If authorized, only owner can change settings
    if github_user and github_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    github_user_name = request.json.get('github_user', '')
    github_repo_name = request.json.get('github_repo', '')

    if not github_user_name or not github_repo_name:
        raise HTTPError(http.BAD_REQUEST)

    changed = github_user_name != github_node.user or github_repo_name != github_node.repo

    # Delete callback
    if changed:

        github_node.delete_hook()

        # Update node settings
        github_node.user = github_user_name
        github_node.repo = github_repo_name

        # Add hook
        github_node.add_hook(save=False)

        github_node.save()


def _page_content(node, github, hotlink=True):

    if github.user is None or github.repo is None:
        return {}

    connect = GitHub.from_settings(github.user_settings)

    branch = request.args.get('branch', None)

    registration_data = (
        github.registration_data.get('branches', [])
        if github.owner.is_registration
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

    # If authorization, check whether authorized user has push rights to repo
    has_auth = False
    if github.user_settings:
        repo = connect.repo(github.user, github.repo)
        has_auth = repo is not None and repo['permissions']['push']

    hgrid = tree_to_hgrid(
        tree['tree'], github.user, github.repo, node,
        ref=commit_id, hotlink=hotlink,
    )

    return {
        'gh_user': github.user,
        'repo': github.repo,
        'has_auth': has_auth,
        'api_url': node.api_url,
        'branches': branches,
        'commit_id': commit_id,
        'show_commit_id': branch != commit_id,
        'grid_data': json.dumps(hgrid),
        'registration_data': json.dumps(registration_data),
    }


@must_be_contributor_or_public
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
def github_get_repo(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')

    connect = GitHub.from_settings(github.user_settings)

    data = connect.repo(github.user, github.repo)

    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
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

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')
    archive = kwargs.get('archive', 'tar')

    connect = GitHub.from_settings(github.user_settings)

    headers, data = connect.starball(github.user, github.repo, archive)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


@must_be_contributor
@must_have_addon('github', 'node')
def github_set_privacy(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = node.get_addon('github')
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = GitHub.from_settings(github.user_settings)

    connect.set_privacy(github.user, github.repo, private)


@must_be_contributor
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
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
@must_have_addon('github', 'node')
def github_oauth_delete_node(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github_node = node.get_addon('github')

    github_node.user_settings = None
    github_node.save()

    github_node.delete_hook()

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
            github_node.add_hook(save=False)
            github_node.save()

    # TODO: Handle redirect with no node
    return redirect(os.path.join(node.url, 'settings'))
