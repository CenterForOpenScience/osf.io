"""

"""

import os
import json
import datetime
import httplib as http

from mako.template import Template
from hurry.filesize import size, alternative
from flask import request, make_response

from framework.auth import get_current_user
from framework.flask import redirect  # VOL-aware redirect
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website import models
from website import settings
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from .api import Bitbucket, tree_to_hgrid
from .auth import oauth_start_url, oauth_get_token


@must_be_logged_in
def bitbucket_set_user_config(*args, **kwargs):
    return {}


@must_be_contributor
@must_have_addon('bitbucket', 'node')
def bitbucket_set_config(*args, **kwargs):
    bitbucket = kwargs['node_addon']
    bitbucket.user = request.json.get('bitbucket_user', '')
    bitbucket.repo = request.json.get('bitbucket_repo', '')
    bitbucket.save()


def _page_content(node, bitbucket, data, hotlink=True):
    return {}


@must_be_contributor_or_public
@must_have_addon('bitbucket', 'node')
def bitbucket_page(*args, **kwargs):

    user = kwargs['auth'].user
    node = kwargs['node'] or kwargs['project']
    bitbucket = kwargs['node_addon']

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
@must_have_addon('bitbucket', 'node')
def bitbucket_get_repo(*args, **kwargs):
    bitbucket = kwargs['node_addon']
    connect = Bitbucket.from_settings(bitbucket.user_settings)
    data = connect.repo(bitbucket.user, bitbucket.repo)
    return {'data': data}


@must_be_contributor_or_public
@must_have_addon('bitbucket', 'node')
def bitbucket_download_file(*args, **kwargs):

    bitbucket = kwargs['node_addon']

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
@must_have_addon('bitbucket', 'node')
def bitbucket_download_starball(*args, **kwargs):

    bitbucket = kwargs['node_addon']
    archive = kwargs.get('archive', 'tar')

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    headers, data = connect.starball(bitbucket.user, bitbucket.repo, archive)

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp


@must_be_contributor
@must_have_addon('bitbucket', 'node')
def bitbucket_set_privacy(*args, **kwargs):

    bitbucket = kwargs['node_addon']
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Bitbucket.from_settings(bitbucket.user_settings)

    connect.set_privacy(bitbucket.user, bitbucket.repo, private)


@must_be_contributor
@must_have_addon('bitbucket', 'node')
def bitbucket_add_user_auth(*args, **kwargs):

    user = kwargs['auth'].user

    bitbucket_user = user.get_addon('bitbucket')
    bitbucket_node = kwargs['node_addon']

    if bitbucket_node is None or bitbucket_user is None:
        raise HTTPError(http.BAD_REQUEST)

    bitbucket_node.user_settings = bitbucket_user
    bitbucket_node.save()

    return {}


@must_be_logged_in
def bitbucket_oauth_start(*args, **kwargs):

    user = get_current_user()

    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None
    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    user.add_addon('bitbucket')
    bitbucket_user = user.get_addon('bitbucket')

    if node:
        bitbucket_node = node.get_addon('bitbucket')
        bitbucket_node.user_settings = bitbucket_user
        bitbucket_node.save()

    request_token, request_token_secret, authorization_url = \
        oauth_start_url(user, node)

    bitbucket_user.oauth_request_token = request_token
    bitbucket_user.oauth_request_token_secret = request_token_secret
    bitbucket_user.save()

    return redirect(authorization_url)


@must_have_addon('bitbucket', 'user')
def bitbucket_oauth_delete_user(*args, **kwargs):

    bitbucket_user = kwargs['user_addon']

    bitbucket_user.oauth_access_token = None
    bitbucket_user.save()

    return {}


@must_be_contributor
@must_have_addon('bitbucket', 'node')
def bitbucket_oauth_delete_node(*args, **kwargs):

    bitbucket_node = kwargs['node_addon']

    bitbucket_node.user_settings = None
    bitbucket_node.save()

    return {}


def bitbucket_oauth_callback(*args, **kwargs):

    user = models.User.load(kwargs.get('uid'))
    node = models.Node.load(kwargs.get('nid'))

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    bitbucket_user = user.get_addon('bitbucket')
    if bitbucket_user is None:
        raise HTTPError(http.BAD_REQUEST)

    bitbucket_node = node.get_addon('bitbucket')

    access_token, access_token_secret = oauth_get_token(
        bitbucket_user.oauth_request_token,
        bitbucket_user.oauth_request_token_secret,
        request.args.get('oauth_verifier')
    )

    if access_token is None or access_token_secret is None:
        raise HTTPError(http.BAD_REQUEST)

    bitbucket_user.oauth_request_token = None
    bitbucket_user.oauth_request_token_secret = None
    bitbucket_user.oauth_access_token = access_token
    bitbucket_user.oauth_access_token_secret = access_token_secret

    bitbucket_user.save()

    if bitbucket_node:
        bitbucket_node.user_settings = bitbucket_user
        bitbucket_node.save()

    if node:
        return redirect(os.path.join(node.url, 'settings'))
    return redirect('/settings/')
