import os
import httplib as http

from framework import request, redirect
from framework.auth import get_current_user
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from ..api import GitHub
from ..auth import oauth_start_url, oauth_get_token


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

        # Add webhook
        if github_node.user and github_node.repo:
            github_node.add_hook()

        github_node.save()

    authorization_url, state = oauth_start_url(user, node)

    github_user.oauth_state = state
    github_user.save()

    return redirect(authorization_url)


@must_have_addon('github', 'user')
def github_oauth_delete_user(*args, **kwargs):

    github_user = kwargs['user_addon']

    # Remove webhooks
    for node_settings in github_user.addongithubnodesettings__authorized:
        node_settings.delete_hook()

    # Revoke access token
    connection = GitHub.from_settings(github_user)
    connection.revoke_token()

    github_user.oauth_access_token = None
    github_user.oauth_token_type = None
    github_user.save()

    return {}


@must_be_contributor
@must_have_addon('github', 'node')
def github_oauth_delete_node(*args, **kwargs):

    github_node = kwargs['node_addon']

    # Remove webhook
    github_node.delete_hook()

    github_node.user_settings = None
    github_node.save()

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

    connection = GitHub.from_settings(github_user)
    user = connection.user()

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
