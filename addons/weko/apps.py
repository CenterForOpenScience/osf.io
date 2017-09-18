import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder

weko_root_folder = generic_root_folder('weko')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)

class WEKOAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.weko'
    label = 'addons_weko'
    full_name = 'WEKO'
    short_name = 'weko'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = 128  # MB
    node_settings_template = os.path.join(TEMPLATE_PATH, 'weko_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'weko_user_settings.mako')

    @property
    def get_hgrid_data(self):
        return weko_root_folder

    INDEX_LINKED = 'weko_index_linked'
    INDEX_CREATED = 'weko_index_created'
    FILE_ADDED = 'weko_file_added'
    FILE_REMOVED = 'weko_file_removed'
    INDEX_CREATED = 'weko_index_created'
    ITEM_CREATED = 'weko_item_created'
    NODE_AUTHORIZED = 'weko_node_authorized'
    NODE_DEAUTHORIZED = 'weko_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'weko_node_deauthorized_no_user'

    actions = (INDEX_LINKED,
        INDEX_CREATED,
        FILE_ADDED,
        FILE_REMOVED,
        INDEX_CREATED,
        ITEM_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER)

    @property
    def routes(self):
        from . import routes
        return [routes.oauth_routes, routes.api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
