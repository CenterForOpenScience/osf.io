import os
import logging
import httplib as http

from framework import request, redirect
from framework.auth import get_current_user
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_have_permission
from website.project.decorators import must_have_addon
from website.util import web_url_for

from ..api import GitHub
from ..auth import oauth_start_url, oauth_get_token


logger = logging.getLogger(__name__)


def get_profile_view(user_settings):
    return {
        'url': user_settings.url
    }


@must_have_permission('write')
@must_have_addon('github', 'user')
@must_have_addon('github', 'node')
def github_add_user_auth(user_addon, node_addon, **kwargs):
    node_addon.authorize(user_addon, save=True)
    return {}


@must_be_logged_in
def github_oauth_start(**kwargs):

    user = get_current_user()

    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None

    # Fail if node provided and user not contributor
    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    user.add_addon('github')
    user_settings = user.get_addon('github')

    if node:
        github_node = node.get_addon('github')
        github_node.user_settings = user_settings
        github_node.save()

    authorization_url, state = oauth_start_url(user, node)

    user_settings.oauth_state = state
    user_settings.save()

    return redirect(authorization_url)


def github_oauth_callback(**kwargs):

    user = models.User.load(kwargs.get('uid'))
    node = models.Node.load(kwargs.get('nid'))

    if user is None:
        raise HTTPError(http.NOT_FOUND)
    if kwargs.get('nid') and not node:
        raise HTTPError(http.NOT_FOUND)

    user_settings = user.get_addon('github')
    if user_settings is None:
        raise HTTPError(http.BAD_REQUEST)

    if user_settings.oauth_state != request.args.get('state'):
        raise HTTPError(http.BAD_REQUEST)

    node_settings = node.get_addon('github') if node else None

    code = request.args.get('code')
    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    token = oauth_get_token(code)

    user_settings.oauth_state = None
    user_settings.oauth_access_token = token['access_token']
    user_settings.oauth_token_type = token['token_type']

    connection = GitHub.from_settings(user_settings)
    user = connection.user()

    user_settings.github_user = user.login

    user_settings.save()

    if node_settings:
        node_settings.user_settings = user_settings
        if node_settings.user and node_settings.repo:
            node_settings.add_hook(save=False)
        node_settings.save()

    if node:
        return redirect(os.path.join(node.url, 'settings'))
    return redirect(web_url_for('user_addons'))


@must_have_addon('github', 'user')
def github_oauth_delete_user(user_addon, **kwargs):
    user_addon.clear_auth(save=True)
    return {}


@must_have_permission('write')
@must_have_addon('github', 'node')
def github_oauth_deauthorize_node(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return {}
