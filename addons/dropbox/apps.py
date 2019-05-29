from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.dropbox.settings import MAX_UPLOAD_SIZE


dropbox_root_folder = generic_root_folder('dropbox')

class DropboxAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.dropbox'
    label = 'addons_dropbox'
    full_name = 'Dropbox'
    short_name = 'dropbox'
    configs = ['accounts', 'node']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE
    owners = ['user', 'node']
    categories = ['storage']

    @property
    def get_hgrid_data(self):
        return dropbox_root_folder

    @property
    def routes(self):
        from . import routes
        return [routes.auth_routes, routes.api_routes]

    FOLDER_SELECTED = 'dropbox_folder_selected'
    NODE_AUTHORIZED = 'dropbox_node_authorized'
    NODE_DEAUTHORIZED = 'dropbox_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
