from addons.base.apps import BaseAddonAppConfig

from addons.figshare.views import figshare_root_folder


class FigshareAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.figshare'
    label = 'addons_figshare'
    full_name = 'figshare'
    short_name = 'figshare'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = 50  # MB

    @property
    def get_hgrid_data(self):
        return figshare_root_folder

    FIGSHARE_FOLDER_CREATED = 'figshare_folder_created'
    FIGSHARE_FOLDER_SELECTED = 'figshare_folder_selected'
    FIGSHARE_CONTENT = 'figshare_content_unlinked'
    FIGSHARE_FILE_ADDED = 'figshare_file_added'
    FIGSHARE_FILE_REMOVED = 'figshare_file_removed'
    FIGSHARE_NODE_AUTHORIZED = 'figshare_node_authorized'
    FIGSHARE_NODE_DEAUTHORIZED = 'figshare_node_deauthorized'
    FIGSHARE_NODE_DEAUTHORIZED_NO_USER = 'figshare_node_deauthorized_no_user'

    actions = (
        FIGSHARE_FOLDER_CREATED,
        FIGSHARE_FOLDER_SELECTED,
        FIGSHARE_CONTENT,
        FIGSHARE_FILE_ADDED,
        FIGSHARE_FILE_REMOVED,
        FIGSHARE_NODE_AUTHORIZED,
        FIGSHARE_NODE_DEAUTHORIZED,
        FIGSHARE_NODE_DEAUTHORIZED_NO_USER)

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
