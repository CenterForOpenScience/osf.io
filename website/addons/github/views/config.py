import httplib as http

from framework import request
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from ..api import GitHub


@must_be_logged_in
def github_set_user_config(*args, **kwargs):
    return {}


@must_be_contributor
@must_have_addon('github', 'node')
def github_set_config(*args, **kwargs):

    user = kwargs['auth'].user

    github_node = kwargs['node_addon']
    github_user = github_node.user_settings

    # If authorized, only owner can change settings
    if github_user and github_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    # Parse request
    github_user_name = request.json.get('github_user', '')
    github_repo_name = request.json.get('github_repo', '')

    # Verify that repo exists and that user can access
    connection = GitHub.from_settings(github_user)
    repo = connection.repo(github_user_name, github_repo_name)
    if repo is None:
        if github_user:
            message = (
                'Cannot access repo. Either the repo does not exist '
                'or your account does not have permission to view it.'
            )
        else:
            message = (
                'Cannot access repo.'
            )
        return {'message': message}, http.BAD_REQUEST

    if not github_user_name or not github_repo_name:
        raise HTTPError(http.BAD_REQUEST)

    changed = (
        github_user_name != github_node.user or
        github_repo_name != github_node.repo
    )

    # Update hooks
    if changed:

        # Delete existing hook, if any
        github_node.delete_hook()

        # Update node settings
        github_node.user = github_user_name
        github_node.repo = github_repo_name

        # Add new hook
        if github_node.user and github_node.repo:
            github_node.add_hook(save=False)

        github_node.save()

    return {}



@must_be_contributor
@must_have_addon('github', 'node')
def github_set_privacy(*args, **kwargs):

    github = kwargs['node_addon']
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(github.user_settings)

    connection.set_privacy(github.user, github.repo, private)

