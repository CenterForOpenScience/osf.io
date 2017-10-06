import os

from addons.base.apps import BaseAddonAppConfig, generic_root_folder

cloudfiles_root_folder = generic_root_folder('cloudfiles')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class CloudFilesAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.cloudfiles'
    label = 'addons_cloudfiles'
    full_name = 'Cloud Files'
    short_name = 'cloudfiles'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True

    node_settings_template = os.path.join(TEMPLATE_PATH, 'cloudfiles_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'cloudfiles_user_settings.mako')

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

    @property
    def get_hgrid_data(self):
        return cloudfiles_root_folder
