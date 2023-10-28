import os

from addons.base.apps import BaseAddonAppConfig
from addons.boa.settings import MAX_UPLOAD_SIZE

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, 'templates')


class BoaAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.boa'
    label = 'addons_boa'
    full_name = 'Boa'
    short_name = 'boa'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['Remote computing']
    has_hgrid_files = False
    node_settings_template = os.path.join(TEMPLATE_PATH, 'boa_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'boa_user_settings.mako')
    max_file_size = MAX_UPLOAD_SIZE

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
