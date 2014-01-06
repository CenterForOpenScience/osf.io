"""

"""

import os
import json
import datetime
import httplib as http

from mako.template import Template
from hurry.filesize import size, alternative

from framework import request, redirect, make_response
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


def _page_content(node, github, data, hotlink=True):

    if github.user is None or github.repo is None:
        return github.render_config_error(data)

    connect = GitHub.from_settings(github)

    branch = request.args.get('branch', None)

    registration_data = (
        github.registration_data.get('branches', [])
        if github.registered
        else []
    )

    # Get data from GitHub API
    branches = connect.branches(github.user, github.repo)
    if branches is None:
        return github.render_config_error(data)
    if hotlink:
        repo = connect.repo(github.user, github.repo)
        if repo is None or repo['private']:
            hotlink = False

    commit_id, tree = connect.tree(
        github.user, github.repo, branch=branch,
        registration_data=registration_data
    )
    if tree is None:
        return github.render_config_error(data)

    hgrid = tree_to_hgrid(
        tree['tree'], github.user, github.repo, node, commit_id, hotlink,
    )

    return Template('''

        <div class="row">

            <div class="col-md-6">

                <h4>Viewing ${gh_user} / ${repo}</h4>

                % if len(branches) > 1:

                    <form role="form">
                        <select id="gitBranchSelect" name="branch">
                            % for branch in branches:
                                <option
                                    value=${branch['name']}
                                    ${'selected' if commit_id in [branch['name'], branch['commit']['sha']] else ''}
                                >${branch['name']}</option>
                            % endfor
                        </select>
                    </form>

                % endif

            </div>

            <div class="col-md-6">

                <h4>Downloads</h4>

                <p><a href="${api_url}github/tarball/">Tarball</a></p>
                <p><a href="${api_url}github/zipball/">Zip</a></p>

            </div>

        </div>

        % if user['can_edit']:

            % if has_auth:

                <div class="container" style="position: relative;">
                    <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="gitFormUpload">click here</a>) to upload files</h3>
                    <div id="fallback"></div>
                    <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
                        <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
                    </div>
                </div>

            % else:

                <p>
                    This GitHub add-on has not been authenticated. To enable file uploads and deletion,
                    browse to the <a href="${node['url']}settings/">settings</a> page and authenticate this add-on.
                <p>

            % endif

        % endif

        <div id="grid">
            <div id="gitCrumb"></div>
            <div id="gitGrid"></div>
        </div>

        <script type="text/javascript">

            // Import JS variables
            var gridData = ${grid_data},
                ref = '${commit_id}',
                canEdit = ${int(user['can_edit'])},
                hasAuth = ${int(has_auth)};

            // Submit branch form on change
            % if len(branches) > 1:
                $('#gitBranchSelect').on('change', function() {
                    $(this).closest('form').submit();
                });
            % endif

        </script>
    ''').render(
        gh_user=github.user,
        repo=github.repo,
        has_auth=github.oauth_access_token is not None,
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
    github = _get_addon(node)

    data = _view_project(node, user)

    content = _page_content(node, github, data)

    rv = {
        'addon_title': 'GitHub',
        'addon_page': content,
        'addon_page_js': github.config.include_js['page'],
        'addon_page_css': github.config.include_css['page'],
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
@must_not_be_registration
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
                    'url': node.api_url + 'github/file/' + os.path.join(path, filename),
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
@must_not_be_registration
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
    author = {
        'name': user.fullname,
        'email': '{0}@osf.io'.format(user._id),
    }

    connect = GitHub.from_settings(github)

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
def github_set_privacy(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = GitHub.from_settings(github)

    connect.set_privacy(github.user, github.repo, private)


@must_be_contributor
@must_have_addon('github')
def github_oauth_start(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    auth_url, state = oauth_start_url(user, node)

    github.oauth_state = state
    github.save()

    return redirect(auth_url)


@must_be_contributor
@must_have_addon('github')
def github_oauth_delete(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    github.oauth_access_token = None
    github.save()

    return {}


# TODO: Handle auth for users as well as nodes
def github_oauth_callback(*args, **kwargs):

    verification_key = request.args.get('state')
    user = models.User.load(kwargs.get('uid', None))
    node = models.Node.load(kwargs.get('nid', None))

    if node is None:
        raise HTTPError(http.NOT_FOUND)

    github = _get_addon(node)

    if github.oauth_state != verification_key:
        raise HTTPError(http.BAD_REQUEST)

    code = request.args.get('code')

    if code is not None:

        token = oauth_get_token(code)

        github.oauth_osf_user = user
        github.oauth_state = None
        github.oauth_access_token = token

        github.save()

    return redirect(os.path.join(node.url, 'settings'))
