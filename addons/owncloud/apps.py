import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.owncloud.settings import MAX_UPLOAD_SIZE

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

owncloud_root_folder = generic_root_folder('owncloud')

class OwnCloudAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.owncloud'
    label = 'addons_owncloud'
    full_name = 'ownCloud'
    short_name = 'owncloud'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    node_settings_template = os.path.join(TEMPLATE_PATH, 'owncloud_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'owncloud_user_settings.mako')
    max_file_size = MAX_UPLOAD_SIZE

    @property
    def get_hgrid_data(self):
        return owncloud_root_folder

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
