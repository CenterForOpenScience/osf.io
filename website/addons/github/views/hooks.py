from dateutil.parser import parse as dateparse

from framework import request

from website import models
from website.project.decorators import must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from website.addons.github import utils


# TODO: Refactor using NodeLogger
def add_hook_log(node, github, action, path, date, committer, url=None,
                 sha=None, save=False):

    github_data = {
        'user': github.user,
        'repo': github.repo,
    }
    if url:
        github_data['url'] = '{0}github/file/{1}/'.format(
            node.api_url,
            path
        )
        if sha:
            github_data['url'] += '?ref=' + sha

    node.add_log(
        action=action,
        params={
            'project': node.parent_id,
            'node': node._id,
            'path': path,
            'github': github_data,
        },
        auth=None,
        foreign_user=committer,
        log_date=date,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('github', 'node')
def github_hook_callback(node_addon, **kwargs):
    """Add logs for commits from outside OSF.

    """
    if request.json is None:
        return {}

    # Fail if hook signature is invalid
    utils.verify_hook_signature(
        node_addon,
        request.data,
        request.headers,
    )

    node = kwargs['node'] or kwargs['project']

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] and commit['message'] in utils.MESSAGES.values():
            continue

        _id = commit['id']
        date = dateparse(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            add_hook_log(
                node, node_addon, 'github_' + models.NodeLog.FILE_ADDED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('modified', []):
            add_hook_log(
                node, node_addon, 'github_' + models.NodeLog.FILE_UPDATED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('removed', []):
            add_hook_log(
                node, node_addon, 'github_' + models.NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
