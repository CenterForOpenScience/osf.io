"""

"""


import os
import re
import json
import urllib
import datetime
import pygments
import httplib as http

from hurry.filesize import size, alternative
from dateutil.parser import parse as dateparse

from framework import request, redirect, make_response
from framework.auth import get_current_user, must_be_logged_in
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

from .api import GitHub, raw_url, tree_to_hgrid
from .auth import oauth_start_url, oauth_get_token

MESSAGE_BASE = 'via the Open Science Framework'
MESSAGES = {
    'add': 'Added {0}'.format(MESSAGE_BASE),
    'update': 'Updated {0}'.format(MESSAGE_BASE),
    'delete': 'Deleted {0}'.format(MESSAGE_BASE),
}

# All GitHub hooks come from 192.30.252.0/22
HOOKS_IP = '192.30.252.'

SHA1 = re.compile(r'^\w{40}$')

def _add_hook_log(node, github, action, path, date, committer, url=None, sha=None, save=False):

    github_data = {
        'user': github.user,
        'repo': github.repo,
    }
    if url:
        github_data['url'] = '{0}github/file/{1}/'.format(
            node.api_url,
            path
        )
        if sha:
            github_data['url'] += '?ref=' + sha

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
    github = kwargs['node_addon']

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] and commit['message'] in MESSAGES.values():
            continue

        _id = commit['id']
        date = dateparse(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_ADDED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('modified', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_UPDATED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('removed', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()


@must_be_logged_in
def github_set_user_config(*args, **kwargs):
    return {}


@must_be_contributor
@must_have_addon('github', 'node')
def github_set_config(*args, **kwargs):

    user = kwargs['user']

    github_node = kwargs['node_addon']
    github_user = github_node.user_settings

    # If authorized, only owner can change settings
    if github_user and github_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    # Parse request
    github_user_name = request.json.get('github_user', '')
    github_repo_name = request.json.get('github_repo', '')

    # Verify that repo exists and that user can access
    connect = GitHub.from_settings(github_user)
    repo = connect.repo(github_user_name, github_repo_name)
    if repo is None:
        if github_user:
            message = (
                'Cannot access repo. Either the repo does not exist '
                'or your account does not have permission to view it.'
            )
        else:
            message = (
                'Cannot access repo.'
            )
        return {'message': message}, 400

    if not github_user_name or not github_repo_name:
        raise HTTPError(http.BAD_REQUEST)

    changed = (
        github_user_name != github_node.user or
        github_repo_name != github_node.repo
    )

    # Delete callback
    if changed:

        github_node.delete_hook()

        # Update node settings
        github_node.user = github_user_name
        github_node.repo = github_repo_name

        # Add hook
        if github_node.user and github_node.repo:
            github_node.add_hook(save=False)

        github_node.save()


def _page_content(node, github, branch=None, sha=None, hotlink=True):

    # Fail if GitHub settings incomplete
    if github.user is None or github.repo is None:
        return {}

    repo = None

    connect = GitHub.from_settings(github.user_settings)

    if sha and not branch:
        raise HTTPError(http.BAD_REQUEST)

    # Get default branch if not provided
    if not branch:
        repo = repo or connect.repo(github.user, github.repo)
        if not repo:
            return {}
        branch = repo['default_branch']

    # Get registered branches if provided
    registered_branches = (
        github.registration_data.get('branches', [])
        if github.owner.is_registration
        else []
    )
    registered_branch_names = [
        _branch['name']
        for _branch in registered_branches
    ]

    # Fail if registered and branch not in registration data
    if registered_branches and branch not in registered_branch_names:
        raise HTTPError(http.BAD_REQUEST)

    if sha:
        branches = connect.branches(github.user, github.repo, branch)
        head = branches['commit']['sha']
    else:
        head = None

    # Use registered SHA if provided
    for _branch in registered_branches:
        if branch == _branch['name']:
            sha = _branch['commit']['sha']

    # Get data from GitHub API if not registered
    branches = registered_branches or connect.branches(github.user, github.repo)
    if branches is None:
        return {}

    # Check repo privacy if hotlinking enabled
    if hotlink:
        repo = connect.repo(github.user, github.repo)
        if repo is None or repo['private']:
            hotlink = False

    # Get file tree
    tree = connect.tree(
        github.user, github.repo, sha=sha or branch,
        registration_data=registered_branches
    )
    if tree is None:
        raise HTTPError(http.BAD_REQUEST)

    # Check permissions if authorized
    has_auth = False
    if github.user_settings:
        repo = repo or connect.repo(github.user, github.repo)
        has_auth = repo is not None and repo['permissions']['push']

    # Build HGrid JSON
    hgrid = tree_to_hgrid(
        tree['tree'], github.user, github.repo, node,
        branch=branch, sha=sha, hotlink=hotlink,
    )

    return {
        'complete': True,
        'gh_user': github.user,
        'repo': github.repo,
        'has_auth': has_auth,
        'is_head': sha is None or sha == head,
        'api_url': node.api_url,
        'branches': branches,
        'branch': branch,
        'sha': sha if sha else '',
        'ref': sha or branch,
        'grid_data': json.dumps(hgrid),
        'registration_data': json.dumps(registered_branches),
    }


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_widget(*args, **kwargs):
    github = kwargs['node_addon']
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
    github = kwargs['node_addon']

    data = _view_project(node, user, primary=True)
    branch, sha = request.args.get('branch'), request.args.get('sha')
    rv = _page_content(node, github, branch=branch, sha=sha)
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
    github = kwargs['node_addon']
    connect = GitHub.from_settings(github.user_settings)
    data = connect.repo(github.user, github.repo)
    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = kwargs['node_addon']

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')

    connect = GitHub.from_settings(github.user_settings)

    name, data, _ = connect.file(github.user, github.repo, path, ref=ref)
    if data is None:
        raise HTTPError(http.NOT_FOUND)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
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

    connect = GitHub.from_settings(github.user_settings)

    repo = connect.repo(github.user, github.repo)

    # Get branch / commit
    branch = request.args.get('branch', repo['default_branch'])
    sha = request.args.get('sha', branch)

    file_name, data, size = connect.file(
        github.user, github.repo, path, ref=sha,
    )

    # Get file URL
    if repo is None or repo['private']:
        url = os.path.join(node.api_url, 'github', 'file', path)
    else:
        url = raw_url(github.user, github.repo, sha, path)

    # Get file history
    start_sha = (sha or branch) if node.is_registration else branch
    commits = connect.history(github.user, github.repo, path, sha=start_sha)
    for commit in commits:
        if repo['private']:
            commit['download'] = os.path.join(node.api_url, 'github', 'file', path) + '?ref=' + commit['sha']
        else:
            commit['download'] = raw_url(github.user, github.repo, commit['sha'], path)
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

    connect = GitHub.from_settings(github.user_settings)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    content = upload.read()

    # Get SHA of existing file if present; requires an additional call to the
    # GitHub API
    tree = connect.tree(github.user, github.repo, sha=sha or branch)
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

        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.')

        info = {
            'name': filename,
            'uid': os.path.join('__repo__', data['content']['path']),
            'parent_uid': 'tree:' + '||'.join(['__repo__', path]).strip('||'),
            'ext': ext,
            'size': [
                data['content']['size'],
                size(data['content']['size'], system=alternative)
            ],
            'type': 'file',
            'sha': data['content']['sha'],
            'url': data['content']['url'],
            'download': node.api_url + 'github/file/{0}/'.format(os.path.join(path, filename)),
            'view': os.path.join(node.url, 'github', 'file', path, filename),
            'delete': node.api_url + 'github/file/{0}/'.format(data['content']['path']),
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

    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    connect = GitHub.from_settings(github.user_settings)

    data = connect.delete_file(
        github.user, github.repo, path, MESSAGES['delete'],
        sha=sha, author=author,
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

    connect = GitHub.from_settings(github.user_settings)
    headers, data = connect.starball(github.user, github.repo, archive, ref)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


@must_be_contributor
@must_have_addon('github', 'node')
def github_set_privacy(*args, **kwargs):

    github = kwargs['node_addon']
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = GitHub.from_settings(github.user_settings)

    connect.set_privacy(github.user, github.repo, private)


@must_be_contributor
@must_have_addon('github', 'node')
def github_add_user_auth(*args, **kwargs):

    user = kwargs['user']

    github_user = user.get_addon('github')
    github_node = kwargs['node_addon']

    if github_node is None or github_user is None:
        raise HTTPError(http.BAD_REQUEST)

    github_node.user_settings = github_user
    github_node.save()

    return {}


@must_be_logged_in
def github_oauth_start(*args, **kwargs):

    user = get_current_user()

    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None

    # Fail if node provided and user not contributor
    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    user.add_addon('github')
    github_user = user.get_addon('github')

    if node:
        github_node = node.get_addon('github')
        github_node.user_settings = github_user
        github_node.save()

    authorization_url, state = oauth_start_url(user, node)

    github_user.oauth_state = state
    github_user.save()

    return redirect(authorization_url)


@must_have_addon('github', 'user')
def github_oauth_delete_user(*args, **kwargs):

    github_user = kwargs['user_addon']

    github_user.oauth_access_token = None
    github_user.oauth_token_type = None
    github_user.save()

    return {}


@must_be_contributor
@must_have_addon('github', 'node')
def github_oauth_delete_node(*args, **kwargs):

    github_node = kwargs['node_addon']

    github_node.user_settings = None
    github_node.save()

    github_node.delete_hook()

    return {}


def github_oauth_callback(*args, **kwargs):

    user = models.User.load(kwargs.get('uid'))
    node = models.Node.load(kwargs.get('nid'))

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    github_user = user.get_addon('github')
    if github_user is None:
        raise HTTPError(http.BAD_REQUEST)

    if github_user.oauth_state != request.args.get('state'):
        raise HTTPError(http.BAD_REQUEST)

    github_node = node.get_addon('github') if node else None

    code = request.args.get('code')
    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    token = oauth_get_token(code)

    github_user.oauth_state = None
    github_user.oauth_access_token = token['access_token']
    github_user.oauth_token_type = token['token_type']

    connect = GitHub.from_settings(github_user)
    user = connect.user()

    github_user.github_user = user['login']

    github_user.save()

    if github_node:
        github_node.user_settings = github_user
        if github_node.user and github_node.repo:
            github_node.add_hook(save=False)
        github_node.save()

    if node:
        return redirect(os.path.join(node.url, 'settings'))
    return redirect('/settings/')
