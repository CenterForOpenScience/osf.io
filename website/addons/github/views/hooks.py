import httplib as http
import logging

from dateutil.parser import parse as dateparse

from framework import request
from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from .util import MESSAGES


# All GitHub hooks come from 192.30.252.0/22
HOOKS_IP = '192.30.252.'

logger = logging.getLogger(__name__)

def _add_hook_log(node, github, action, path, date, committer, url=None, sha=None, save=False):

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
def github_hook_callback(**kwargs):
    """Add logs for commits from outside OSF.

    """
    if request.json is None:
        return {}

    # Request must come from GitHub hooks IP
    if not request.json.get('test'):
        if HOOKS_IP not in request.remote_addr:
            raise HTTPError(http.BAD_REQUEST)

    node = kwargs['node'] or kwargs['project']
    github = kwargs['node_addon']

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] and commit['message'] in MESSAGES.values():
            continue

        _id = commit['id']
        date = dateparse(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_ADDED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('modified', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_UPDATED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('removed', []):
            _add_hook_log(
                node, github, 'github_' + models.NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
