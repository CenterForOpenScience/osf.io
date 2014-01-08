"""

"""

import os
import json
import datetime
import httplib as http

from mako.template import Template
from hurry.filesize import size, alternative

from framework import request, redirect, make_response
from framework.auth import get_current_user
from framework.exceptions import HTTPError

from website import models
from website import settings
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import Bitbucket, tree_to_hgrid
from .auth import oauth_start_url, oauth_get_token


@must_be_contributor
@must_have_addon('bitbucket')
def bitbucket_settings(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')

    bitbucket.user = request.json.get('bitbucket_user', '')
    bitbucket.repo = request.json.get('bitbucket_repo', '')
    bitbucket.save()


def _page_content(node, bitbucket, data, hotlink=True):

    if bitbucket.user is None or bitbucket.repo is None:
        return bitbucket.render_config_error(data)

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    branch = request.args.get('branch', None)

    registration_data = (
        bitbucket.registration_data.get('branches', [])
        if bitbucket.registered
        else []
    )

    # Get data from Bitbucket API
    branches = connect.branches(bitbucket.user, bitbucket.repo)
    if branches is None:
        return bitbucket.render_config_error(data)
    if hotlink:
        repo = connect.repo(bitbucket.user, bitbucket.repo)
        if repo is None or repo['private']:
            hotlink = False

    commit_id, tree = connect.tree(
        bitbucket.user, bitbucket.repo, branch=branch,
        registration_data=registration_data
    )
    if tree is None:
        return bitbucket.render_config_error(data)

    hgrid = tree_to_hgrid(
        tree['tree'], bitbucket.user, bitbucket.repo, node, commit_id, hotlink,
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

                <p><a href="${api_url}bitbucket/tarball/">Tarball</a></p>
                <p><a href="${api_url}bitbucket/zipball/">Zip</a></p>

            </div>

        </div>

        <hr />

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

            // Import JS variables
            var gridData = ${grid_data};
            var ref = '${commit_id}';
            var canEdit = ${int(user['can_edit'])};

            // Submit branch form on change
            % if len(branches) > 1:
                $('#gitBranchSelect').on('change', function() {
                    $(this).closest('form').submit();
                });
            % endif

        </script>
    ''').render(
        gh_user=bitbucket.user,
        repo=bitbucket.repo,
        api_url=node.api_url,
        branches=branches,
        commit_id=commit_id,
        grid_data=json.dumps(hgrid),
        **data
    )


@must_be_contributor_or_public
@must_have_addon('bitbucket')
def bitbucket_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')

    data = _view_project(node, user)

    content = _page_content(node, bitbucket, data)

    rv = {
        'addon_title': 'Bitbucket',
        'addon_page': content,
        'addon_page_js': bitbucket.config.include_js['page'],
        'addon_page_css': bitbucket.config.include_css['page'],
    }
    rv.update(data)
    return rv


@must_be_contributor_or_public
@must_have_addon('bitbucket')
def bitbucket_get_repo(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    data = connect.repo(bitbucket.user, bitbucket.repo)

    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('bitbucket')
def bitbucket_download_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')

    path = kwargs.get('path')
    if path is None:
        raise HTTPError(http.NOT_FOUND)

    ref = request.args.get('ref')

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    name, data = connect.file(bitbucket.user, bitbucket.repo, path, ref=ref)

    resp = make_response(data)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        name
    )
    return resp


@must_be_contributor_or_public
@must_have_addon('bitbucket')
def bitbucket_download_starball(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')
    archive = kwargs.get('archive', 'tar')

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    headers, data = connect.starball(bitbucket.user, bitbucket.repo, archive)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


@must_be_contributor
@must_have_addon('bitbucket')
def bitbucket_set_privacy(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket = node.get_addon('bitbucket')
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    connect.set_privacy(bitbucket.user, bitbucket.repo, private)


@must_be_contributor
@must_have_addon('bitbucket')
def bitbucket_add_user_auth(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    bitbucket_node = node.get_addon('bitbucket')
    bitbucket_user = user.get_addon('bitbucket')

    if bitbucket_node is None or bitbucket_user is None:
        raise HTTPError(http.BAD_REQUEST)

    bitbucket_node.user_settings = bitbucket_user
    bitbucket_node.save()

    return {}


@must_be_contributor
@must_have_addon('bitbucket')
def bitbucket_oauth_start(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    user.add_addon('bitbucket', 'user')
    bitbucket_user = user.get_addon('bitbucket')
    bitbucket_node = node.get_addon('bitbucket')

    bitbucket_node.user_settings = bitbucket_user
    bitbucket_node.save()

    request_token, request_token_secret, authorization_url = \
        oauth_start_url(user, node)

    bitbucket_user.oauth_request_token = request_token
    bitbucket_user.oauth_request_token_secret = request_token_secret
    bitbucket_user.save()

    return redirect(authorization_url)


# TODO: Expose this
def bitbucket_oauth_delete_user(*args, **kwargs):

    user = get_current_user()
    bitbucket_user = user.get_addon('bitbucket')

    bitbucket_user.oauth_access_token = None
    bitbucket_user.save()

    return {}


@must_be_contributor
@must_have_addon('bitbucket')
def bitbucket_oauth_delete_node(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    bitbucket_node = node.get_addon('bitbucket')

    bitbucket_node.user_settings = None
    bitbucket_node.save()

    return {}


def bitbucket_oauth_callback(*args, **kwargs):

    user = models.User.load(kwargs.get('uid', None))
    node = models.Node.load(kwargs.get('nid', None))

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    bitbucket_user = user.get_addon('bitbucket')
    bitbucket_node = node.get_addon('bitbucket')

    verifier = request.args.get('oauth_verifier')

    access_token, access_token_secret = oauth_get_token(
        bitbucket_user.oauth_request_token,
        bitbucket_user.oauth_request_token_secret,
        verifier
    )

    bitbucket_user.oauth_request_token = None
    bitbucket_user.oauth_request_token_secret = None
    bitbucket_user.oauth_access_token = access_token
    bitbucket_user.oauth_access_token_secret = access_token_secret

    bitbucket_user.save()

    if bitbucket_node:
        bitbucket_node.user_settings = bitbucket_user
        bitbucket_node.save()

    # TODO: Handle redirect with no node
    return redirect(os.path.join(node.url, 'settings'))
