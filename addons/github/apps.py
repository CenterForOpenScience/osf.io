import logging
import os

from addons.base.apps import BaseAddonAppConfig
from addons.github.api import GitHubClient, ref_to_params
from addons.github.exceptions import NotFoundError, GitHubError
from addons.github.settings import MAX_UPLOAD_SIZE
from addons.github.utils import get_refs, check_permissions
from website.util import rubeus

logger = logging.getLogger(__name__)

logging.getLogger('github3').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)

def github_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = GitHubClient(external_account=node_settings.external_account)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public and not node.is_contributor_or_group_member(auth.user):
        try:
            repo = connection.repo(node_settings.user, node_settings.repo)
        except NotFoundError:
            logger.error('Could not access GitHub repo')
            return None
        except GitHubError:
            return
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
        'view': True,
        'private': node_settings.is_private
    }
    urls = {
        'upload': node_settings.owner.api_url + 'github/file/' + (ref or ''),
        'fetch': node_settings.owner.api_url + 'github/hgrid/' + (ref or ''),
        'branch': node_settings.owner.api_url + 'github/hgrid/root/',
        'zip': node_settings.owner.api_url + 'github/zipball/' + (ref or ''),
        'repo': 'https://github.com/{0}/{1}/tree/{2}'.format(node_settings.user, node_settings.repo, branch)
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
        private_key=kwargs.get('view_only', None),
    )]

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(
    HERE,
    'templates',
    'github_node_settings.mako',
)

class GitHubAddonConfig(BaseAddonAppConfig):

    name = 'addons.github'
    label = 'addons_github'
    full_name = 'GitHub'
    short_name = 'github'
    configs = ['accounts', 'node']
    categories = ['storage']
    owners = ['user', 'node']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE
    node_settings_template = NODE_SETTINGS_TEMPLATE

    @property
    def get_hgrid_data(self):
        return github_hgrid_data

    FILE_ADDED = 'github_file_added'
    FILE_REMOVED = 'github_file_removed'
    FILE_UPDATED = 'github_file_updated'
    FOLDER_CREATED = 'github_folder_created'
    NODE_AUTHORIZED = 'github_node_authorized'
    NODE_DEAUTHORIZED = 'github_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'github_node_deauthorized_no_user'
    REPO_LINKED = 'github_repo_linked'

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
