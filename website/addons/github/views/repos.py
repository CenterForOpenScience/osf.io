import httplib as http
from github3 import GitHubError

from framework.flask import request
from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth, must_be_logged_in

from website.project.decorators import must_have_addon

from ..api import GitHub


@must_be_logged_in
@must_have_addon('github', 'user')
def github_list_repos(**kwargs):

    user_settings = kwargs['user_addon']
    if not user_settings.has_auth:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(user_settings)
    return list(connection.repos())


@must_be_logged_in
@must_have_addon('github', 'user')
def github_create_repo(**kwargs):

    repo_name = request.json.get('name')
    if not repo_name:
        raise HTTPError(http.BAD_REQUEST)

    user_settings = kwargs['user_addon']
    connection = GitHub.from_settings(user_settings)

    try:
        repo = connection.create_repo(repo_name)
    except GitHubError:
        # TODO: Check status code
        raise HTTPError(http.BAD_REQUEST)

    return {
        'user': repo.owner.login,
        'repo': repo.name,
    }
