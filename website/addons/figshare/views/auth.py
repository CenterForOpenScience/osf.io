import os
import httplib as http

from framework import request, redirect
from framework.auth import get_current_user
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from ..api import Figshare
from ..auth import oauth_start_url, oauth_get_token
from ..settings import API_URL, API_OAUTH_URL

@must_be_logged_in
def figshare_oauth_start(*args, **kwargs):

    user = get_current_user()

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


@must_be_contributor
@must_have_addon('figshare', 'node')
def figshare_oauth_delete_node(*args, **kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = node.get_addon('figshare')

    node_settings.user_settings = None
    node_settings.figshare_id = None
    node_settings.figshare_type = None
    node_settings.figshare_title = None
    node_settings.save()

    node.add_log(
        action='figshare_content_unlinked',
        params={
            'project': node.parent_id,
            'node': node._id,
            'figshare': {
                'type': node_settings.figshare_type,
                'id': node_settings.figshare_id
            }
        },
        auth=auth,
    )

    return {}


@must_have_addon('figshare', 'user')
def figshare_oauth_delete_user(*args, **kwargs):

    figshare_user = kwargs['user_addon']

    figshare_user.oauth_access_token = None
    figshare_user.oauth_token_type = None
    figshare_user.save()

    return {}


def figshare_oauth_callback(*args, **kwargs):

    user = get_current_user()

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
    return redirect('/settings/')


@must_be_contributor
@must_have_addon('figshare', 'node')
def figshare_add_user_auth(*args, **kwargs):

    user = kwargs['auth'].user
    node = kwargs['node'] or kwargs['project']

    figshare_node = node.get_addon('figshare')
    figshare_user = user.get_addon('figshare')

    if figshare_node is None or figshare_user is None:
        raise HTTPError(http.BAD_REQUEST)

    figshare_node.user_settings = figshare_user
    # ensure api url is correct
    figshare_node.save()

    return {}

# TODO: Expose this


def figshare_oauth_delete_user(*args, **kwargs):

    user = get_current_user()
    figshare_user = user.get_addon('figshare')

    figshare_user.oauth_access_token = None
    figshare_user.oauth_token_type = None
    figshare_user.save()

    return {}
