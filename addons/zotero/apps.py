import os
from addons.base.apps import BaseAddonAppConfig

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(
    HERE,
    'templates',
    'zotero_node_settings.mako',
)

class ZoteroAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.zotero'
    label = 'addons_zotero'
    full_name = 'Zotero'
    short_name = 'zotero'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    views = ['widget']
    categories = ['citations']
    has_hgrid_files = False
    widget_help = 'Zotero'
    node_settings_template = NODE_SETTINGS_TEMPLATE

    FOLDER_SELECTED = 'zotero_folder_selected'
    NODE_AUTHORIZED = 'zotero_node_authorized'
    NODE_DEAUTHORIZED = 'zotero_node_deauthorized'
    LIBRARY_SELECTED = 'zotero_library_selected'

    actions = (
        FOLDER_SELECTED,
        LIBRARY_SELECTED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED)

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
