# -*- coding: utf-8 -*-

import httplib as http

from flask import request
from github3 import GitHubError

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_have_addon

from ..api import GitHub


@must_be_logged_in
@must_have_addon('github', 'user')
@must_have_addon('github', 'node')
def github_create_repo(node_addon, **kwargs):

    user = kwargs['auth'].user
    repo_name = request.json.get('repo_name')

    if not repo_name:
        raise HTTPError(http.BAD_REQUEST)

    user_settings = kwargs['user_addon']
    connection = GitHub.from_settings(user_settings)

    try:
        repo = connection.create_repo(repo_name)
    except GitHubError:
        # TODO: Check status code
        raise HTTPError(http.BAD_REQUEST)

    return node_addon.to_json(user)