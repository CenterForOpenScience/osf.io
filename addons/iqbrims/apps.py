from addons.base.apps import BaseAddonAppConfig, generic_root_folder

iqbrims_root_folder = generic_root_folder('iqbrims')

class IQBRIMSAddonConfig(BaseAddonAppConfig):

    name = 'addons.iqbrims'
    label = 'addons_iqbrims'
    full_name = 'IQB-RIMS'
    short_name = 'iqbrims'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True

    @property
    def get_hgrid_data(self):
        return iqbrims_root_folder

    FOLDER_SELECTED = 'iqbrims_folder_selected'
    NODE_AUTHORIZED = 'iqbrims_node_authorized'
    NODE_DEAUTHORIZED = 'iqbrims_node_deauthorized'

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
