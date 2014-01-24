import httplib as http

from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from ..api import GitHub


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_widget(*args, **kwargs):

    github = kwargs['node_addon']
    connection = GitHub.from_settings(github.user_settings)

    # Check whether user has view access to repo
    complete = False
    if github.user and github.repo:
        repo = connection.repo(github.user, github.repo)
        if repo:
            complete = True

    if github:
        rv = {
            'complete': complete,
            'short_url': github.short_url,
        }
        rv.update(github.config.to_json())
        return rv
    raise HTTPError(http.NOT_FOUND)


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_get_repo(*args, **kwargs):
    github = kwargs['node_addon']
    connection = GitHub.from_settings(github.user_settings)
    data = connection.repo(github.user, github.repo)
    return {'data': data}
