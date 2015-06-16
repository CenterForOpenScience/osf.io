# -*- coding: utf-8 -*-

import httplib as http

from flask import request
from github3 import GitHubError

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_have_addon
from website.addons.github.utils import get_repo_dropdown

from ..api import GitHub


@must_be_logged_in
@must_have_addon('github', 'user')
@must_have_addon('github', 'node')
def github_create_repo(auth, node_addon, **kwargs):

    user = auth.user
    repo_name = request.json.get('repo_name')

    if not repo_name:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(node_addon.api.account)

    try:
        repo = connection.create_repo(repo_name, auto_init=True)
    except GitHubError:
        # TODO: Check status code
        raise HTTPError(http.BAD_REQUEST)

    return {
        'repo_names': get_repo_dropdown(user, node_addon)['repo_names'],
        'user_names': get_repo_dropdown(user, node_addon)['user_names'],
        'user': user.username
    }
