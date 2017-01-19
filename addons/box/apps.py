from addons.base.apps import BaseAddonAppConfig

from addons.box.views import box_root_folder

class BoxAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.box'
    label = 'addons_box'
    full_name = 'Box'
    short_name = 'box'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = 250  # MB

    @property
    def get_hgrid_data(self):
        return box_root_folder

    FOLDER_SELECTED = 'box_folder_selected'
    NODE_AUTHORIZED = 'box_node_authorized'
    NODE_DEAUTHORIZED = 'box_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

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
