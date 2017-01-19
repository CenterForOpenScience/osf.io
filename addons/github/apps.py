import os
from addons.base.apps import BaseAddonAppConfig

from addons.github.views import github_hgrid_data

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
    max_file_size = 100  # MB
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
