# -*- coding: utf-8 -*-
import logging

from flask import request
from github3 import GitHubError

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus

from website.addons.github.api import GitHub, ref_to_params
from website.addons.github.utils import get_refs, check_permissions
from website.addons.github.exceptions import NotFoundError


logger = logging.getLogger(__name__)

logging.getLogger('github3').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)


def github_repo_url(owner, repo, branch):
    url = "https://github.com/{0}/{1}/tree/{2}".format(owner, repo, branch)
    return url


def github_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = GitHub.from_settings(node_settings.user_settings)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public and not node.is_contributor(auth.user):
        try:
            repo = connection.repo(node_settings.user, node_settings.repo)
        except NotFoundError:
            # TODO: Test me @jmcarp
            # TODO: Add warning message
            logger.error('Could not access GitHub repo')
            return None
        if repo.private:
            return None

    try:
        branch, sha, branches = get_refs(
            node_settings,
            branch=kwargs.get('branch'),
            sha=kwargs.get('sha'),
            connection=connection,
        )
    except (NotFoundError, GitHubError):
        # TODO: Show an alert or change GitHub configuration?
        logger.error('GitHub repo not found')
        return

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = check_permissions(
            node_settings, auth, connection, branch, sha, repo=repo,
        )
    else:
        ref = None
        can_edit = False

    name_tpl = '{user}/{repo}'.format(
        user=node_settings.user, repo=node_settings.repo
    )

    permissions = {
        'edit': can_edit,
        'view': True
    }
    urls = {
        'upload': node_settings.owner.api_url + 'github/file/' + (ref or ''),
        'fetch': node_settings.owner.api_url + 'github/hgrid/' + (ref or ''),
        'branch': node_settings.owner.api_url + 'github/hgrid/root/',
        'zip': node_settings.owner.api_url + 'github/zipball/' + (ref or ''),
        'repo': github_repo_url(owner=node_settings.user, repo=node_settings.repo, branch=branch)
    }

    branch_names = [each.name for each in branches]
    if not branch_names:
        branch_names = [branch]  # if repo un-init-ed then still add default branch to list of branches

    return [rubeus.build_addon_root(
        node_settings,
        name_tpl,
        urls=urls,
        permissions=permissions,
        branches=branch_names,
        defaultBranch=branch,
    )]


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_root_folder_public(*args, **kwargs):
    """View function returning the root container for a GitHub repo. In
    contrast to other add-ons, this is exposed via the API for GitHub to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return github_hgrid_data(node_settings, auth=auth, **data)
