from addons.base.apps import BaseAddonAppConfig
from website import settings
from addons.osfstorage import settings as addon_settings
from addons.osfstorage import views


class OSFStorageAddonAppConfig(BaseAddonAppConfig):
    name = 'addons.osfstorage'
    label = 'addons_osfstorage'
    full_name = 'OSF Storage'
    short_name = 'osfstorage'
    added_default = ['node']
    added_mandatory = ['node']

    has_hgrid_files = True

    get_hgrid_data = views.osf_storage_root

    OWNERS = ['node']

    WATERBUTLER_CREDENTIALS = addon_settings.WATERBUTLER_CREDENTIALS

    WATERBUTLER_SETTINGS = addon_settings.WATERBUTLER_SETTINGS

    WATERBUTLER_RESOURCE = addon_settings.WATERBUTLER_RESOURCE

    DISK_SAVING_MODE = settings.DISK_SAVING_MODE

    FOLDER_SELECTED = 'osfstorage_folder_selected'
    NODE_AUTHORIZED = 'osfstorage_node_authorized'
    NODE_DEAUTHORIZED = 'osfstorage_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
