from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.googledriveinstitutions.settings import MAX_UPLOAD_SIZE

googledriveinstitutions_root_folder = generic_root_folder('googledriveinstitutions')

class GoogleDriveInstitutionsAddonConfig(BaseAddonAppConfig):

    name = 'addons.googledriveinstitutions'
    label = 'addons_googledriveinstitutions'
    full_name = 'Google Drive in G Suite / Google Workspace'
    short_name = 'googledriveinstitutions'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE

    @property
    def get_hgrid_data(self):
        return googledriveinstitutions_root_folder

    FOLDER_SELECTED = 'googledriveinstitutions_folder_selected'
    NODE_AUTHORIZED = 'googledriveinstitutions_node_authorized'
    NODE_DEAUTHORIZED = 'googledriveinstitutions_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    # default value for RdmAddonOption.is_allowed for GRDM Admin
    is_allowed_default = False

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
