import os

from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.onedrivebusiness import SHORT_NAME, FULL_NAME
from addons.onedrivebusiness import settings

onedrivebusiness_root_folder = generic_root_folder('onedrivebusiness')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class OneDriveBusinessAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)
    full_name = FULL_NAME
    short_name = SHORT_NAME

    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']

    has_hgrid_files = True

    max_file_size = settings.MAX_UPLOAD_SIZE

    # No node setting views for Institution Storage
    user_settings_template = os.path.join(TEMPLATE_PATH, 'user_settings.mako')

    # default value for RdmAddonOption.is_allowed for GRDM Admin
    is_allowed_default = False
    for_institutions = True

    FILE_ADDED = 'onedrivebusiness_file_added'
    FILE_REMOVED = 'onedrivebusiness_file_removed'
    FILE_UPDATED = 'onedrivebusiness_file_updated'
    FOLDER_CREATED = 'onedrivebusiness_folder_created'
    NODE_AUTHORIZED = 'onedrivebusiness_node_authorized'
    NODE_DEAUTHORIZED = 'onedrivebusiness_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'onedrivebusiness_node_deauthorized_no_user'
    actions = (
        FILE_ADDED,
        FILE_REMOVED,
        FILE_UPDATED,
        FOLDER_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER
    )

    @property
    def get_hgrid_data(self):
        return onedrivebusiness_root_folder

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
