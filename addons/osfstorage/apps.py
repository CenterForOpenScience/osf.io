from addons.base.apps import BaseAddonAppConfig
from website import settings
from addons.osfstorage import settings as addon_settings
from addons.osfstorage import views

# Ensure blinker signal listeners are connected
import addons.osfstorage.listeners  # noqa


class OSFStorageAddonAppConfig(BaseAddonAppConfig):
    name = 'addons.osfstorage'
    label = 'addons_osfstorage'
    full_name = 'OSF Storage'
    short_name = 'osfstorage'
    added_default = ['node']
    added_mandatory = ['node']

    categories = ['storage']

    has_hgrid_files = True

    get_hgrid_data = views.osf_storage_root

    max_file_size = 5 * 1024  # 5 GB
    high_max_file_size = 5 * 1024  # 5 GB

    owners = ['node']

    WATERBUTLER_CREDENTIALS = addon_settings.WATERBUTLER_CREDENTIALS

    WATERBUTLER_SETTINGS = addon_settings.WATERBUTLER_SETTINGS

    WATERBUTLER_RESOURCE = addon_settings.WATERBUTLER_RESOURCE

    DISK_SAVING_MODE = settings.DISK_SAVING_MODE

    FOLDER_SELECTED = 'osfstorage_folder_selected'
    NODE_AUTHORIZED = 'osfstorage_node_authorized'
    NODE_DEAUTHORIZED = 'osfstorage_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def routes(self):
        from addons.osfstorage import routes
        return [routes.api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
