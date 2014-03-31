import logging
import httplib as http
from flask import request
from dateutil.parser import parse as parse_date

from framework.exceptions import HTTPError
from framework.auth.decorators import Auth

from website.models import User
from website.project.decorators import must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.utils import resolve_gitlab_author


logger = logging.getLogger(__name__)

def add_hook_log(node_settings, commit, save=False):
    """Log a commit through GitLab hooks. Use the associated OSF user if one
    can be inferred through the commit email, else use the plaintext name
    from the hook payload.

    :param AddonGitlabNodeSettings node_settings: Node settings instance
    :param dict commit: Commit payload
    :param bool save: Save changes

    """
    # Skip if pushed by OSF
    if commit['message'] and commit['message'] in gitlab_settings.MESSAGES.values():
        return

    node = node_settings.owner

    sha = commit['id']
    date = parse_date(commit['timestamp'])

    user = resolve_gitlab_author(commit['author'])
    auth = Auth(user=user) if isinstance(user, User) else None

    node.add_log(
        action='gitlab_commit_added',
        params={
            'project': node.parent_id,
            'node': node._id,
            'gitlab': {
                'sha': sha,
            }
        },
        foreign_user=user if not isinstance(user,  User) else None,
        log_date=date,
        auth=auth,
        save=save,
    )


@must_be_valid_project
@must_not_be_registration
@must_have_addon('gitlab', 'node')
def gitlab_hook_callback(**kwargs):
    """Add logs for commits from outside OSF.

    """
    # Request must come from GitLab hooks IP, unless testing
    if not request.json.get('test'):
        if gitlab_settings.HOST not in request.remote_addr:
            raise HTTPError(http.BAD_REQUEST)

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    # Log commits
    for commit in request.json.get('commits', []):
        add_hook_log(node_settings, commit, save=False)

    # Save accumulated changes
    node.save()
