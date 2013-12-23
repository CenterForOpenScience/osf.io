"""

"""

import json
import httplib as http

from mako.template import Template

from framework import request, make_response
from framework.exceptions import HTTPError

from website import settings
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project

from . import api

@must_be_contributor
def github_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addongithubsettings__addons
    if addons:
        github = addons[0]
        github.user = request.json.get('github_user', '')
        github.repo = request.json.get('github_repo', '')
        github.save()
    else:
        raise HTTPError(http.BAD_REQUEST)

@must_be_contributor
def github_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('github')
        node.save()
    except ValueError:
        pass

@must_be_contributor_or_public
def github_page(**kwargs):

    user = kwargs.get('user')
    node = kwargs.get('node') or kwargs.get('project')

    addons = node.addongithubsettings__addons
    if not addons:
        raise HTTPError(http.BAD_REQUEST)

    github = addons[0]

    config = settings.ADDONS_AVAILABLE_DICT['github']

    branches = api.get_branches(github.user, github.repo)

    branch = request.args.get('branch', None)

    commit_id, tree = api.get_tree(github.user, github.repo, branch=branch)
    hgrid = api.tree_to_hgrid(tree['tree'], github.repo, node)

    content = Template('''
        <h4>Viewing ${repo} / ${commit_id}</h4>

        <hr />

        <a href="${api_url}github/tarball/">Download tarball</a>

        <hr />

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

        <div id="gitCrumb"></div>
        <div id="gitGrid"></div>

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

    rv = {
        'addon_title': 'GitHub',
        'addon_page': content,
        'addon_page_js': config.include_js['page'],
        'addon_page_css': config.include_css['page'],

    }
    rv.update(_view_project(node, user))
    return rv

@must_be_contributor_or_public
def github_download_file(**kwargs):

    node = kwargs['node'] or kwargs['project']

    addons = node.addongithubsettings__addons
    if not addons:
        raise HTTPError(http.BAD_REQUEST)

    github = addons[0]

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    name, data = api.get_file(github.user, github.repo, path)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
    return resp

@must_be_contributor_or_public
def github_download_tarball(**kwargs):

    node = kwargs['node'] or kwargs['project']

    addons = node.addongithubsettings__addons
    if not addons:
        raise HTTPError(http.BAD_REQUEST)

    github = addons[0]

    headers, data = api.get_tarball(github.user, github.repo)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp