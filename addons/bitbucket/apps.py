import logging
import os

from addons.base.apps import BaseAddonAppConfig
from addons.bitbucket.api import BitbucketClient, ref_to_params
from addons.bitbucket.exceptions import NotFoundError
from addons.bitbucket.utils import get_refs
from website.util import rubeus

logger = logging.getLogger(__name__)


def bitbucket_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = BitbucketClient(access_token=node_settings.external_account.oauth_key)

    node = node_settings.owner
    if node.is_public and not node.is_contributor(auth.user):
        try:
            connection.repo(node_settings.user, node_settings.repo)
        except NotFoundError:
            # TODO: Add warning message
            logger.error('Could not access Bitbucket repo')
            return None

    try:
        branch, sha, branches = get_refs(
            node_settings,
            branch=kwargs.get('branch'),
            sha=kwargs.get('sha'),
            connection=connection,
        )
    except (NotFoundError, Exception):
        # TODO: Show an alert or change Bitbucket configuration?
        logger.error('Bitbucket repo not found')
        return

    ref = None if branch is None else ref_to_params(branch, sha)

    name_tpl = '{user}/{repo}'.format(
        user=node_settings.user, repo=node_settings.repo
    )

    permissions = {
        'edit': False,
        'view': True,
        'private': node_settings.is_private
    }
    urls = {
        'upload': None,
        'fetch': node_settings.owner.api_url + 'bitbucket/hgrid/' + (ref or ''),
        'branch': node_settings.owner.api_url + 'bitbucket/hgrid/root/',
        'zip': node_settings.owner.api_url + 'bitbucket/zipball/' + (ref or ''),
        'repo': 'https://bitbucket.com/{0}/{1}/branch/'.format(node_settings.user, node_settings.repo)
    }

    branch_names = [each['name'] for each in branches]
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
    'bitbucket_node_settings.mako',
)

class BitbucketAddonConfig(BaseAddonAppConfig):

    name = 'addons.bitbucket'
    label = 'addons_bitbucket'
    full_name = 'Bitbucket'
    short_name = 'bitbucket'
    configs = ['accounts', 'node']
    categories = ['storage']
    owners = ['user', 'node']
    has_hgrid_files = True
    node_settings_template = NODE_SETTINGS_TEMPLATE

    @property
    def get_hgrid_data(self):
        return bitbucket_hgrid_data

    FILE_ADDED = 'bitbucket_file_added'
    FILE_REMOVED = 'bitbucket_file_removed'
    FILE_UPDATED = 'bitbucket_file_updated'
    FOLDER_CREATED = 'bitbucket_folder_created'
    NODE_AUTHORIZED = 'bitbucket_node_authorized'
    NODE_DEAUTHORIZED = 'bitbucket_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'bitbucket_node_deauthorized_no_user'
    REPO_LINKED = 'bitbucket_repo_linked'

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
