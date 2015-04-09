# -*- coding: utf-8 -*-

import httplib as http
import itertools

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message
from framework.exceptions import HTTPError

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
# from website.addons.github.utils import serialize_urls
from website.addons.github.utils import get_repo_dropdown
from website.addons.github.serializer import GitHubSerializer

from ..api import GitHub



@must_be_logged_in
def github_get_user_accounts(auth):
    """View for getting a JSON representation of the logged-in user's
    GitHub user settings.
    """
    user_settings = auth.user.get_addon('github')
    return GitHubSerializer(user_settings=user_settings).serialized_user_settings

@must_be_logged_in
def github_set_user_config(**kwargs):
    return {}


@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_set_config(auth, node_addon, **kwargs):
    """Update GithubNodeSettings based on submitted account and folder information."""

    args = request.get_json()
    external_list_id = args.get('external_list_id')
    external_list_name = args.get('external_list_name')
    node_addon.set_target_folder(external_list_id, external_list_name, auth)
    result = GitHubSerializer(
        node_settings=node_addon,
        user_settings=auth.user.get_addon('github')
    ).serialized_node_settings
    return result

@must_have_addon('github', 'node')
@must_have_permission('read')
def github_get_config(auth, node_addon, **kwargs):
    result = GitHubSerializer(
        node_settings=node_addon,
        user_settings=auth.user.get_addon('github')
    ).serialized_node_settings
    return result


@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_remove_node_settings(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return node_addon.to_json(auth.user)

@must_be_logged_in
@must_have_addon('github', 'user')
def github_remove_user_settings(user_addon, **kwargs):
    success = user_addon.revoke_auth(save=True)
    if not success:
        push_status_message(
            'Your GitHub credentials were removed from the OSF, but we were '
            'unable to revoke your OSF information from GitHub. Your GitHub '
            'credentials may no longer be valid.'
        )
        return {'message': 'reload'}, http.BAD_REQUEST


# WIP, need to get repo_list stuff from model.py into here
@must_be_logged_in
@must_have_addon('github', 'node')
@must_have_permission('write')
@must_not_be_registration
def github_repo_list(auth, node_addon, **kwargs):
    node = node_addon.owner
    user = auth.user
    return get_repo_dropdown(user, node_addon)


@must_have_permission('write')
@must_have_addon('github', 'node')
def github_set_privacy(**kwargs):

    github = kwargs['node_addon']
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(github.user_settings)

    connection.set_privacy(github.user, github.repo, private)

