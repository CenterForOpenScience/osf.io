import logging
import os

from addons.base.apps import BaseAddonAppConfig
from addons.gitlab.api import GitLabClient, ref_to_params
from addons.gitlab.exceptions import NotFoundError, GitLabError
from addons.gitlab.utils import get_refs, check_permissions
from website.util import rubeus

logger = logging.getLogger(__name__)

def gitlab_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = GitLabClient(external_account=node_settings.external_account)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public or node.is_contributor(auth.user):
        try:
            repo = connection.repo(node_settings.repo_id)
        except NotFoundError:
            logger.error('Could not access GitLab repo')
            return None

    try:
        branch, sha, branches = get_refs(node_settings, branch=kwargs.get('branch'), sha=kwargs.get('sha'), connection=connection)
    except (NotFoundError, GitLabError):
        logger.error('GitLab repo not found')
        return

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = check_permissions(node_settings, auth, connection, branch, sha, repo=repo)
    else:
        ref = ''
        can_edit = False

    permissions = {
        'edit': can_edit,
        'view': True,
        'private': node_settings.is_private
    }
    urls = {
        'upload': node_settings.owner.api_url + 'gitlab/file/' + ref,
        'fetch': node_settings.owner.api_url + 'gitlab/hgrid/' + ref,
        'branch': node_settings.owner.api_url + 'gitlab/hgrid/root/' + ref,
        'zip': 'https://{0}/{1}/repository/archive.zip?branch={2}'.format(node_settings.external_account.oauth_secret, repo['path_with_namespace'], ref),
        'repo': 'https://{0}/{1}/tree/{2}'.format(node_settings.external_account.oauth_secret, repo['path_with_namespace'], ref)
    }

    branch_names = [each['name'] for each in branches]
    if not branch_names:
        branch_names = [branch]  # if repo un-init-ed then still add default branch to list of branches

    return [rubeus.build_addon_root(
        node_settings,
        repo['path_with_namespace'],
        urls=urls,
        permissions=permissions,
        branches=branch_names,
        private_key=kwargs.get('view_only', None),
        default_branch=repo['default_branch'],
    )]

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'gitlab_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'gitlab_user_settings.mako')

class GitLabAddonConfig(BaseAddonAppConfig):

    name = 'addons.gitlab'
    label = 'addons_gitlab'
    full_name = 'GitLab'
    short_name = 'gitlab'
    configs = ['accounts', 'node']
    categories = ['storage']
    owners = ['user', 'node']
    has_hgrid_files = True
    max_file_size = 100  # MB
    node_settings_template = NODE_SETTINGS_TEMPLATE
    user_settings_template = USER_SETTINGS_TEMPLATE

    @property
    def get_hgrid_data(self):
        return gitlab_hgrid_data

    FILE_ADDED = 'gitlab_file_added'
    FILE_REMOVED = 'gitlab_file_removed'
    FILE_UPDATED = 'gitlab_file_updated'
    FOLDER_CREATED = 'gitlab_folder_created'
    NODE_AUTHORIZED = 'gitlab_node_authorized'
    NODE_DEAUTHORIZED = 'gitlab_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'gitlab_node_deauthorized_no_user'
    REPO_LINKED = 'gitlab_repo_linked'

    actions = (
        FILE_ADDED,
        FILE_REMOVED,
        FILE_UPDATED,
        FOLDER_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER,
        REPO_LINKED)

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
