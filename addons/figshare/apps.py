from addons.base.apps import BaseAddonAppConfig
from addons.figshare.settings import MAX_UPLOAD_SIZE

from website.util import rubeus

def figshare_root_folder(node_settings, auth, **kwargs):
    """Return the Rubeus/HGrid-formatted response for the root folder only.

    Identical to the generic_views.root_folder except adds root_folder_type
    to exported data.  Fangorn needs root_folder_type to decide whether to
    display the 'Create Folder' button.
    """
    # Quit if node settings does not have authentication
    if not node_settings.has_auth or not node_settings.folder_id:
        return None
    node = node_settings.owner
    return [rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.fetch_folder_name(),
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
        rootFolderType=node_settings.folder_path,
        private_key=kwargs.get('view_only', None),
    )]

class FigshareAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.figshare'
    label = 'addons_figshare'
    full_name = 'figshare'
    short_name = 'figshare'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE

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
