"""

"""

import os
import json
import uuid
import urlparse
import httplib as http

from mako.template import Template

from framework import request, redirect, make_response
from framework.exceptions import HTTPError

from website import settings
from website import models
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import GitHub, oauth_start_url, oauth_get_token, tree_to_hgrid

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


def _page_content(node, github):

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

    hgrid = tree_to_hgrid(tree['tree'], github.repo, node)

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

        <div id="grid">
            <div id="gitCrumb"></div>
            <div id="gitGrid"></div>
        </div>

        <script type="text/javascript">
            var gridData = ${data};
        </script>
    ''').render(
        repo=github.repo,
        api_url=node.api_url,
        branches=branches,
        commit_id=commit_id,
        data=json.dumps(hgrid),
    )


@must_be_contributor_or_public
@must_have_addon('github')
def github_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    config = settings.ADDONS_AVAILABLE_DICT['github']
    github = _get_addon(node)

    content = _page_content(node, github)

    rv = {
        'addon_title': 'GitHub',
        'addon_page': content,
        'addon_page_js': config.include_js['page'],
        'addon_page_css': config.include_css['page'],
    }
    rv.update(_view_project(node, user))
    return rv


@must_be_contributor_or_public
@must_have_addon('github')
def github_download_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    connect = GitHub.from_settings(github)

    name, data = connect.file(github.user, github.repo, path)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
    return resp


@must_be_contributor_or_public
@must_have_addon('github')
def github_download_tarball(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    github = _get_addon(node)

    connect = GitHub.from_settings(github)

    headers, data = connect.tarball(github.user, github.repo)

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
