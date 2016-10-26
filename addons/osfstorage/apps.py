import os

from addons.base.apps import BaseAddonConfig
from website import settings
from website.addons.osfstorage import views


class OSFStorageAddonConfig(BaseAddonConfig):
    name = 'addons.osfstorage'
    label = 'addons_osfstorage'
    full_name = 'OSFStorage'
    short_name = 'osfstorage'

    has_hgrid_files = True

    get_hgrid_data = views.osf_storage_root

    OWNERS = ['node']

    WATERBUTLER_CREDENTIALS = {
        'storage': {}
    }

    WATERBUTLER_SETTINGS = {
        'storage': {
            'provider': 'filesystem',
            'folder': os.path.join(settings.BASE_PATH, 'osfstoragecache'),
        }
    }

    WATERBUTLER_RESOURCE = 'folder'

    DISK_SAVING_MODE = settings.DISK_SAVING_MODE

    FOLDER_SELECTED = 'osfstorage_folder_selected'
    NODE_AUTHORIZED = 'osfstorage_node_authorized'
    NODE_DEAUTHORIZED = 'osfstorage_node_deauthorized'

    actions = (FOLDER_SELECTED, NODE_AUTHORIZED, NODE_DEAUTHORIZED, )

    # @property
    # def user_settings(self):
    #     return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
