import logging
import httplib as http
from flask import request
from dateutil.parser import parse as parse_date

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError

from website.models import User, NodeLog
from website.project.decorators import must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.services import fileservice
from website.addons.gitlab.utils import (
    resolve_gitlab_hook_author, GitlabNodeLogger
)


logger = logging.getLogger(__name__)


def add_diff_log(node, diff, sha, date, gitlab_user, save=False):
    """

    """
    if diff['new_file']:
        action = NodeLog.FILE_ADDED
    elif diff['deleted_file']:
        action = NodeLog.FILE_REMOVED
    else:
        action = NodeLog.FILE_UPDATED

    path = diff['new_path']

    if isinstance(gitlab_user, User):
        auth = Auth(user=gitlab_user)
        foreign_user = None
    else:
        auth = None
        foreign_user = gitlab_user


    node_logger = GitlabNodeLogger(
        node, auth=auth, foreign_user=foreign_user, path=path, date=date,
        sha=sha
    )
    node_logger.log(action, save=save)


def add_hook_log(node_settings, commit, save=False):
    """Log a commit through GitLab hooks. Use the associated OSF user if one
    can be inferred through the commit email, else use the plaintext name
    from the hook payload.

    :param GitlabNodeSettings node_settings: Node settings instance
    :param dict commit: Commit payload
    :param bool save: Save changes

    """
    # Skip if pushed by OSF
    if commit['message'] and commit['message'] in gitlab_settings.MESSAGES.values():
        return

    node = node_settings.owner

    sha = commit['id']
    date = parse_date(commit['timestamp'])
    gitlab_user = resolve_gitlab_hook_author(commit['author'])

    file_service = fileservice.GitlabFileService(node_settings)
    diffs = file_service.get_commit_diff(commit['id'])

    for diff in diffs:
        add_diff_log(node, diff, sha, date, gitlab_user, save=False)


@must_be_valid_project
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_hook_callback(**kwargs):
    """Add logs for commits from outside OSF.

    """
    # Request must come from GitLab hooks IP, unless testing
    if not request.json.get('test'):
        if gitlab_settings.HOOK_DOMAIN not in request.url:
            raise HTTPError(http.BAD_REQUEST)

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    # Log commits
    for commit in request.json.get('commits', []):
        add_hook_log(node_settings, commit, save=False)

    # Save accumulated changes
    node.save()
