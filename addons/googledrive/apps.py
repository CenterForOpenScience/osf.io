from addons.base.apps import BaseAddonAppConfig

from addons.googledrive.views import googledrive_root_folder

class GoogleDriveAddonConfig(BaseAddonAppConfig):

    name = 'addons.googledrive'
    label = 'addons_googledrive'
    full_name = 'Google Drive'
    short_name = 'googledrive'
    configs = ['accounts', 'node']
    has_hgrid_files = True

    @property
    def get_hgrid_data(self):
        return googledrive_root_folder

    FOLDER_SELECTED = 'googledrive_folder_selected'
    NODE_AUTHORIZED = 'googledrive_node_authorized'
    NODE_DEAUTHORIZED = 'googledrive_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
