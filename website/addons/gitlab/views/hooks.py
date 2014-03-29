# TODO: Finish me @jmcarp
# TODO: Test me @jmcarp

import logging
import httplib as http
from flask import request
from dateutil.parser import parse as parse_date

from framework.exceptions import HTTPError

from website import models
from website.project.decorators import must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from website.addons.gitlab import settings as gitlab_settings


logger = logging.getLogger(__name__)

def _add_hook_log(node_settings, action, path, date, committer, url=False,
                  sha=None, save=False):

    node = node_settings.owner

    gitlab_data = {
        'user': node_settings.user,
        'repo': node_settings.repo,
    }
    if url:
        gitlab_data['url'] = node.web_url_for(
            'gitlab_view_file', path=path, sha=sha
        )

    node.add_log(
        action=action,
        params={
            'project': node.parent_id,
            'node': node._id,
            'path': path,
            'gitlab': gitlab_data,
        },
        auth=None,
        foreign_user=committer,
        log_date=date,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_hook_callback(**kwargs):
    """Add logs for commits from outside OSF.

    """
    if request.json is None:
        return {}

    # Request must come from gitlab hooks IP
    if not request.json.get('test'):
        if gitlab_settings.HOST not in request.remote_addr:
            raise HTTPError(http.BAD_REQUEST)

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    payload = request.json

    for commit in payload.get('commits', []):

        # TODO: Look up OSF user by commit

        # Skip if pushed by OSF
        if commit['message'] and commit['message'] in gitlab_settings.MESSAGES.values():
            continue

        _id = commit['id']
        date = parse_date(commit['timestamp'])
        committer = commit['committer']['name']

        # Add logs
        for path in commit.get('added', []):
            _add_hook_log(
                node_settings, 'gitlab_' + models.NodeLog.FILE_ADDED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('modified', []):
            _add_hook_log(
                node_settings, 'gitlab_' + models.NodeLog.FILE_UPDATED,
                path, date, committer, url=True, sha=_id,
            )
        for path in commit.get('removed', []):
            _add_hook_log(
                node_settings, 'gitlab_' + models.NodeLog.FILE_REMOVED,
                path, date, committer,
            )

    node.save()
