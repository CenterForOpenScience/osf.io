import os
from addons.base.apps import BaseAddonConfig

from website import settings

TEMPLATE_PATH = os.path.join(
    settings.BASE_PATH,
    'addons',
    'owncloud',
    'templates'
)

class OwnCloudAddonConfig(BaseAddonConfig):

    name = 'addons.owncloud'
    label = 'addons_owncloud'
    full_name = 'ownCloud'
    short_name = 'owncloud'
    configs = ['accounts', 'node']
    has_hgrid_files = True
    node_settings_template = os.path.join(TEMPLATE_PATH, 'owncloud_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'owncloud_user_settings.mako')

    @property
    def get_hgrid_data(self):
        # Import here to avoid AppRegistryNotReady error
        from addons.owncloud.views import owncloud_root_folder
        return owncloud_root_folder

    actions = ()

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
