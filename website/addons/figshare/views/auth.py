# -*- coding: utf-8 -*-

import os
import httplib as http

from flask import request

from framework.flask import redirect  # VOL-aware redirect
from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.auth.decorators import must_be_logged_in

from website import models
from website.util import web_url_for
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from framework.status import push_status_message

from ..auth import oauth_start_url, oauth_get_token


@must_be_logged_in
def figshare_oauth_start(auth, **kwargs):
    user = auth.user

    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None

    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    user.add_addon('figshare')
    figshare_user = user.get_addon('figshare')

    if node:
        figshare_node = node.get_addon('figshare')
        figshare_node.user_settings = figshare_user
        figshare_node.save()

    request_token, request_token_secret, authorization_url = oauth_start_url(user, node)

    figshare_user.oauth_request_token = request_token
    figshare_user.oauth_request_token_secret = request_token_secret
    figshare_user.save()

    return redirect(authorization_url)


@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_oauth_delete_node(auth, node_addon, **kwargs):

    node = kwargs['node'] or kwargs['project']

    node_addon.user_settings = None
    node_addon.figshare_id = None
    node_addon.figshare_type = None
    node_addon.figshare_title = None
    node_addon.save()

    node.add_log(
        action='figshare_content_unlinked',
        params={
            'project': node.parent_id,
            'node': node._id,
            'figshare': {
                'type': node_addon.figshare_type,
                'id': node_addon.figshare_id,
            }
        },
        auth=auth,
    )

    return {}


@collect_auth
def figshare_oauth_callback(auth, **kwargs):

    user = auth.user

    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None

    # Fail if node provided and user not contributor
    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    figshare_user = user.get_addon('figshare')

    verifier = request.args.get('oauth_verifier')

    access_token, access_token_secret = oauth_get_token(
        figshare_user.oauth_request_token,
        figshare_user.oauth_request_token_secret,
        verifier
    )
    # Handle request cancellations from FigShare's API
    if not access_token or not access_token_secret:
        push_status_message('FigShare authorization request cancelled.')
        if node:
            return redirect(node.web_url_for('node_setting'))
        return redirect(web_url_for('user_addons'))

    figshare_user.oauth_request_token = None
    figshare_user.oauth_request_token_secret = None
    figshare_user.oauth_access_token = access_token
    figshare_user.oauth_access_token_secret = access_token_secret
    figshare_user.save()

    if node:
        figshare_node = node.get_addon('figshare')

        figshare_node.user_settings = figshare_user
        figshare_node.save()

    if node:
        return redirect(os.path.join(node.url, 'settings'))

    return redirect(web_url_for('user_addons'))


@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_add_user_auth(auth, **kwargs):

    user = auth.user
    node = kwargs['node'] or kwargs['project']

    figshare_node = node.get_addon('figshare')
    figshare_user = user.get_addon('figshare')

    if figshare_node is None or figshare_user is None:
        raise HTTPError(http.BAD_REQUEST)

    figshare_node.user_settings = figshare_user
    # ensure api url is correct
    figshare_node.save()

    return {}


@must_be_logged_in
@must_have_addon('figshare', 'user')
def figshare_oauth_delete_user(user_addon, **kwargs):
    user_addon.remove_auth(save=True)
    return {}
