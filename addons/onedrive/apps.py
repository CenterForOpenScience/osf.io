from addons.base.apps import BaseAddonAppConfig, generic_root_folder

onedrive_root_folder = generic_root_folder('onedrive')

class OneDriveAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.onedrive'
    label = 'addons_onedrive'
    full_name = 'OneDrive'
    short_name = 'onedrive'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True

    @property
    def get_hgrid_data(self):
        return onedrive_root_folder

    FILE_ADDED = 'onedrive_file_added'
    FILE_REMOVED = 'onedrive_file_removed'
    FILE_UPDATED = 'onedrive_file_updated'
    FOLDER_CREATED = 'onedrive_folder_created'
    FOLDER_SELECTED = 'onedrive_folder_selected'
    NODE_AUTHORIZED = 'onedrive_node_authorized'
    NODE_DEAUTHORIZED = 'onedrive_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'onedrive_node_deauthorized_no_user'

    actions = (FILE_ADDED, FILE_REMOVED, FILE_UPDATED, FOLDER_CREATED, FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, NODE_DEAUTHORIZED_NO_USER)

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
