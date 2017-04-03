from addons.base.apps import BaseAddonAppConfig


class MendeleyAddonConfig(BaseAddonAppConfig):

    name = 'addons.mendeley'
    label = 'addons_mendeley'
    full_name = 'Mendeley'
    short_name = 'mendeley'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    views = ['widget']
    categories = ['citations']
    has_hgrid_files = False
    widget_help = 'Mendeley'

    FOLDER_SELECTED = 'mendeley_folder_selected'
    NODE_AUTHORIZED = 'mendeley_node_authorized'
    NODE_DEAUTHORIZED = 'mendeley_node_deauthorized'

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
