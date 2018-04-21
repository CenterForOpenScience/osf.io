import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

nextcloud_root_folder = generic_root_folder('nextcloud')

class NextcloudAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.nextcloud'
    label = 'addons_nextcloud'
    full_name = 'Nextcloud'
    short_name = 'nextcloud'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    node_settings_template = os.path.join(TEMPLATE_PATH, 'nextcloud_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'nextcloud_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return nextcloud_root_folder

    actions = ()

    @property
    def routes(self):
        from .routes import api_routes
        return [api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
