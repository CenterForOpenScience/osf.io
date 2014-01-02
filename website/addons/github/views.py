"""

"""

import os
import json
import uuid
import datetime
import urlparse
import httplib as http

from mako.template import Template
from hurry.filesize import size, alternative

from framework import request, redirect, make_response
from framework.flask import secure_filename
from framework.exceptions import HTTPError

from website import settings
from website import models
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import GitHub, oauth_start_url, oauth_get_token, tree_to_hgrid

MESSAGES = {
    'add': 'Added by Open Science Framework',
    'delete': 'Deleted by Open Science Framework',
}

# TODO: Abstract across add-ons
def _get_addon(node):
    """Get GitHub addon for node.

    :param Node node: Target node
    :return AddonGitHubSettings: GitHub settings

    """
    node = node
    addons = node.addongithubsettings__addons
    if addons:
        return addons[0]
    raise HTTPError(http.BAD_REQUEST)


@must_be_contributor
@must_have_addon('github')
def github_settings(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    github.user = request.json.get('github_user', '')
    github.repo = request.json.get('github_repo', '')
    github.save()


@must_be_contributor
@must_have_addon('github')
def github_disable(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    try:
        node.addons_enabled.remove('github')
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)
    node.save()


def _page_content(node, github, data):

    if github.user is None or github.repo is None:

        return github.render_config_error()

    connect = GitHub.from_settings(github)

    branches = connect.branches(github.user, github.repo)

    branch = request.args.get('branch', None)

    registration_data = (
        github.registration_data.get('branches', [])
        if github.registered
        else []
    )
    commit_id, tree = connect.tree(
        github.user, github.repo, branch=branch,
        registration_data=registration_data
    )
    if tree is None:
        return github.render_config_error()

    hgrid = tree_to_hgrid(tree['tree'], github.repo, node, commit_id)

    return Template('''
        <h4>Viewing ${repo} / ${commit_id}</h4>

        <hr />

        <a href="${api_url}github/tarball/">Download tarball</a>

        <hr />

        % if len(branches) > 1:
            <form role="form">
                <div class="form-group">
                    <label for="selectBranch">Select branch</label>
                    <select id="selectBranch" name="branch">
                        % for branch in branches:
                            <option
                                value=${branch['name']}
                                ${'selected' if commit_id in [branch['name'], branch['commit']['sha']] else ''}
                            >${branch['name']}</option>
                        % endfor
                    </select>
                </div>
                <button class="btn btn-success">Submit</button>
            </form>
            <hr />
        % endif

        % if user['can_edit']:
            <div class="container" style="position: relative;">
                <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="gitFormUpload">click here</a>) to upload files</h3>
                <div id="fallback"></div>
                <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
                    <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
                </div>
            </div>
        % endif

        <div id="grid">
            <div id="gitCrumb"></div>
            <div id="gitGrid"></div>
        </div>

        <script type="text/javascript">
            var gridData = ${grid_data};
            var ref = '${commit_id}';
            var canEdit = ${int(user['can_edit'])};
        </script>
    ''').render(
        repo=github.repo,
        api_url=node.api_url,
        branches=branches,
        commit_id=commit_id,
        grid_data=json.dumps(hgrid),
        **data
    )


@must_be_contributor_or_public
@must_have_addon('github')
def github_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    config = settings.ADDONS_AVAILABLE_DICT['github']
    github = _get_addon(node)

    data = _view_project(node, user)

    content = _page_content(node, github, data)

    rv = {
        'addon_title': 'GitHub',
        'addon_page': content,
        'addon_page_js': config.include_js['page'],
        'addon_page_css': config.include_css['page'],
    }
    rv.update(data)
    return rv


@must_be_contributor_or_public
@must_have_addon('github')
def github_get_repo(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    connect = GitHub.from_settings(github)

    data = connect.repo(github.user, github.repo)

    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('github')
def github_download_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')

    connect = GitHub.from_settings(github)

    name, data = connect.file(github.user, github.repo, path, ref=ref)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
    return resp


@must_be_contributor_or_public
@must_have_addon('github')
def github_upload_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = _get_addon(node)
    now = datetime.datetime.utcnow()

    path = kwargs.get('path', '')

    ref = request.args.get('ref')

    connect = GitHub.from_settings(github)

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

    data = connect.upload_file(
        github.user, github.repo,
        os.path.join(path, filename), MESSAGES['add'], content,
        sha=sha, branch=ref,
    )

    if data is not None:

        node.add_log(
            action=(
                models.NodeLog.FILE_UPDATED
                if sha
                else models.NodeLog.FILE_ADDED
            ),
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'path': os.path.join(path, filename),
                'addon': {
                    'name': 'github',
                    '_id': github._primary_key,
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
            'download': node.api_url + 'github/file/{0}'.format(path),
        }

        if ref is not None:
            info['download'] += '/?ref=' + ref
            info['ref'] = ref

        return [info]

    raise HTTPError(http.BAD_REQUEST)

@must_be_contributor_or_public
@must_have_addon('github')
def github_delete_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    github = _get_addon(node)
    now = datetime.datetime.utcnow()

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')
    sha = request.json.get('sha')

    connect = GitHub.from_settings(github)

    data = connect.delete_file(
        github.user, github.repo, path, MESSAGES['delete'], sha=sha, branch=ref,
    )

    node.add_log(
        action=models.NodeLog.FILE_REMOVED,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'path': path,
            'addon': {
                'name': 'github',
                '_id': github._primary_key,
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
    github = _get_addon(node)
    archive = kwargs.get('archive', 'tar')

    connect = GitHub.from_settings(github)

    headers, data = connect.starball(github.user, github.repo, archive)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


@must_be_contributor
@must_have_addon('github')
def github_oauth_start(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    state = str(uuid.uuid4()) + '_' + user._id
    _, url = oauth_start_url(node, state=state)

    github.oauth_state = state
    github.save()

    return redirect(url)


@must_be_contributor
@must_have_addon('github')
def github_oauth_delete(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    github.oauth_access_token = None
    github.save()

    return {}


def github_oauth_callback(*args, **kwargs):

    verification_key = request.args.get('state')
    node = models.Node.load(kwargs.get('nid', None))

    if node is None:
        raise HTTPError(http.NOT_FOUND)

    github = _get_addon(node)

    if github.oauth_state != verification_key:
        raise HTTPError(http.BAD_REQUEST)

    user = models.User.load(verification_key.split('_')[-1])
    code = request.args.get('code')

    if code is not None:

        req = oauth_get_token(code)

        if req.status_code == 200:
            params = urlparse.parse_qs(req.content)
        else:
            raise HTTPError(http.BAD_REQUEST)

        access_token = params.get('access_token')
        github.oauth_osf_user = user
        github.oauth_state = None
        github.oauth_access_token = access_token[0]
        github.save()

    return redirect(os.path.join(node.url, 'settings'))
