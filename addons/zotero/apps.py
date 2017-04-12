from addons.base.apps import BaseAddonAppConfig


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

    FOLDER_SELECTED = 'zotero_folder_selected'
    NODE_AUTHORIZED = 'zotero_node_authorized'
    NODE_DEAUTHORIZED = 'zotero_node_deauthorized'

    actions = (
        FOLDER_SELECTED,
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
