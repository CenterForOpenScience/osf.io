import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder

swift_root_folder = generic_root_folder('swift')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class SwiftAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.swift'
    label = 'addons_swift'
    full_name = 'OpenStack Swift'
    short_name = 'swift'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = 128  # MB
    node_settings_template = os.path.join(TEMPLATE_PATH, 'swift_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'swift_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return swift_root_folder

    BUCKET_LINKED = 'swift_bucket_linked'
    BUCKET_UNLINKED = 'swift_bucket_unlinked'
    FILE_ADDED = 'swift_file_added'
    FILE_REMOVED = 'swift_file_removed'
    FILE_UPDATED = 'swift_file_updated'
    FOLDER_CREATED = 'swift_folder_created'
    NODE_AUTHORIZED = 'swift_node_authorized'
    NODE_DEAUTHORIZED = 'swift_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'swift_node_deauthorized_no_user'

    actions = (BUCKET_LINKED,
        BUCKET_UNLINKED,
        FILE_ADDED,
        FILE_REMOVED,
        FILE_UPDATED,
        FOLDER_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER)

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
